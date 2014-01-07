from .util import Singleton, LocalSingleton, LocalSingletonBase
from .exceptions import NotFoundException

from sleekxmpp.jid import JID

@LocalSingleton
class FqdnProvider(LocalSingletonBase):
	pass
	
class Fqdn(object):
	pass

@LocalSingleton
class UserProvider(LocalSingletonBase):
	def normalize_jid(self, user, keep_resource=False):
		if isinstance(user, JID):
			if keep_resource:
				return str(user.full)
			else:
				return str(user.bare)
		else:
			# Probably a string, or coercible to one...
			return str(user)
			
	def normalize_user(self, user):
		if isinstance(user, User):
			return user
		else:
			return self.get(user)
		
	def wrap_user(self, row):
		return User(self.identifier, row)
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="users")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such user(s) exist.")
		
		return [self.wrap_user(item) for item in items]
		
	def get(self, jid):
		component = Component.Instance(self.identifier)
		username, fqdn = self.normalize_jid(jid).split("@", 1)
		return self.get_from_query("SELECT * FROM users WHERE `Username` = ? AND `Fqdn` = ? LIMIT 1", (username, component.fqdn))[0]
		
	def find_by_email(self, email):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM users WHERE `EmailAddress` = ? AND `Fqdn` = ?", (email, component.fqdn))
		
	def find_by_nickname(self, nickname):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM users WHERE `Nickname` = ? AND `Fqdn` = ?", (nickname, component.fqdn))[0]
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM users WHERE `Id` = ? AND `Fqdn` = ?", (id_, component.fqdn))[0]
	
class User(object):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
	def load_row(self, row):
		self.id = row["Id"]
		self.jid = "%s@%s" % (row["Username"], row["Fqdn"])
		self.first_name = row["FirstName"]
		self.last_name = row["LastName"]
		self.full_name = "%s %s" % (row["FirstName"], row["LastName"])
		self.email_address = row["EmailAddress"]
		self.phone_number = row["MobileNumber"]
		self.nickname = row["Nickname"]
		self.job_title = row["JobTitle"]
		self.active = bool(row["Active"])
		
	def update_vcard(self, data):
		if "first_name" in data:
			self.row["FirstName"] = data["first_name"]
			
		if "last_name" in data:
			self.row["LastName"] = data["last_name"]
			
		if "job_title" in data:
			self.row["JobTitle"] = data["job_title"]
			
		if "nickname" in data:
			self.row["Nickname"] = data["nickname"]
			
		if "email_address" in data:
			self.row["EmailAddress"] = data["email_address"]
			
		if "phone_number" in data:
			self.row["MobileNumber"] = data["phone_number"]
			
		self.commit_row()
		
	def get_affiliations(self, room=None):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		return affiliation_provider.get_user(self, room=room)
	
	def get_presences(self, room=None):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.get_user(self, room=room)
	
@LocalSingleton
class RoomProvider(LocalSingletonBase):
	def normalize_jid(self, room):
		if isinstance(room, JID):
			return str(room.bare)
		else:
			# Probably a string, or coercible to one...
			return str(room)
			
	def normalize_room(self, room):
		if isinstance(room, Room):
			return room
		else:
			return self.get(room)
		
	def wrap_room(self, row):
		return Room(self.identifier, row)
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="rooms")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such room(s) exist.")
		
		return [self.wrap_room(item) for item in items]
		
	def get(self, jid):
		component = Component.Instance(self.identifier)
		roomname, fqdn = self.normalize_jid(jid).split("@", 1)
		return self.get_from_query("SELECT * FROM rooms WHERE `Node` = ? AND `Fqdn` = ? LIMIT 1", (username, component.fqdn))[0]
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM rooms WHERE `Id` = ? AND `Fqdn` = ?", (id_, component.fqdn))[0]
		
	
class Room(object):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
	def commit_row(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		self.id = row["Id"]
		self.jid = "%s@%s" % (row["Node"], fqdn_provider.find_by_id(row["FqdnId"]).fqdn)
		self.name = row["Name"]
		self.description = row["Description"]
		self.owner = user_provider.find_by_id(row["OwnerId"])
		self.usercount = row["LastUserCount"]
		self.creation_date = row["CreationDate"]
		self.archival_date = row["ArchivalDate"]
		self.private = bool(row["IsPrivate"])
		self.archived = bool(row["IsArchived"])
		
	def increment_usercount(self, amount=1):
		self.row["LastUserCount"] = row["LastUserCount"] + amount
		self.commit_row()
		
	def decrement_usercount(self, amount=1):
		self.row["LastUserCount"] = row["LastUserCount"] + amount
		self.commit_row()
		
	def update_metadata(self, data):
		if "name" in data:
			self.row["Name"] = data["name"]
			
		if "description" in data:
			self.row["Description"] = data["description"]
			
		self.commit_row()
			
	def change_owner(self, user):
		user_provider = UserProvider.Instance(self.identifier)
		self.row["OwnerId"] = user_provider.normalize_user(user).id
		self.commit_row()
	
	def get_affiliations(self, user=None):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		return affiliation_provider.get_room(self, user=user)
	
	def get_presences(self, user=None):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.get_room(self, user=user)
		
@LocalSingleton
class AffiliationProvider(LocalSingletonBase):
	pass
	
class Affiliation(object):
	pass
		
@LocalSingleton
class PresenceProvider(LocalSingletonBase):
	pass
	
class Presence(object):
	pass

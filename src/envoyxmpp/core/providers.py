from .util import Singleton, LocalSingleton, LocalSingletonBase, LazyLoadingObject

import json
from sleekxmpp.jid import JID

@LocalSingleton
class ConfigurationProvider(LocalSingletonBase):
	def read(self, path):
		with open(path, "r") as config_file:
			self.parse(json.load(config_file))
		
	def parse(self, data):
		logger = ApplicationLogger.Instance(self.identifier)
		
		try:
			self.mysql_hostname = data["database"]["hostname"]
			self.mysql_username = data["database"]["username"]
			self.mysql_password = data["database"]["password"]
			self.mysql_database = data["database"]["database"]
		except KeyError, e:
			raise ConfigurationException("All or part of the database connection configuration is missing.")
			
		try:
			self.mock_sms = data["mock"]["sms"]
		except KeyError, e:
			self.mock_sms = False
			
		try:
			self.mock_email = data["mock"]["email"]
		except KeyError, e:
			self.mock_email = False
			
		if self.mock_email == False:
			try:
				self.smtp_hostname = data["smtp"]["hostname"]
				self.smtp_port = data["smtp"]["port"]
				self.smtp_tls = data["smtp"]["tls"]
				self.smtp_username = data["smtp"]["username"]
				self.smtp_password = data["smtp"]["password"]
				self.smtp_sender = data["smtp"]["sender"]
			except KeyError, e:
				raise ConfigurationException("Mock e-mail mode is disabled, but no complete SMTP configuration was provided.")
			
		if self.mock_sms == False:
			try:
				self.twilio_sid = data["twilio"]["sid"]
				self.twilio_token = data["twilio"]["token"]
				self.twilio_sender = data["twilio"]["sender"]
			except KeyError, e:
				raise ConfigurationException("Mock SMS mode is disabled, but no complete Twilio configuration was provided.")
				
		try:
			self.development_mode = data["development_mode"]
		except KeyError, e:
			self.development_mode = False
			
		if self.development_mode == True:
			logger.warning("Development mode is enabled!")

@LocalSingleton
class FqdnProvider(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
	
	def normalize_fqdn(self, fqdn):
		if isinstance(fqdn, Fqdn):
			return fqdn
		else:
			return self.get(fqdn)
		
	def wrap(self, row):
		item = Fqdn(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="fqdns")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such FQDN(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, host):
		return self.get_from_query("SELECT * FROM fqdns WHERE `Fqdn` = ? LIMIT 1", (host,))[0]
		
	def find_by_id(self, id_):
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM fqdns WHERE `Id` = ? LIMIT 1", (id_,))[0]
		
		return self.cache[id_]
	
class Fqdn(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"owner": self.get_owner
		}
		
	def load_row(self, row):
		self.id = row["Id"]
		self.fqdn = row["Fqdn"]
		self.name = row["Name"]
		self.description = row["Description"]
		self._owner = row["UserId"]
				
	def get_owner(self):
		user_provider = UserProvider.Instance(self.identifier)
		return user_provider.find_by_id(self._owner)
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def update_metadata(self, data):
		if "name" in data:
			self.row["Name"] = data["name"]
			
		if "description" in data:
			self.row["Description"] = data["description"]
			
		self.commit()
		
	def change_owner(self, user):
		user_provider = UserProvider.Instance(self.identifier)
		self.row["OwnerId"] = user_provider.normalize_user(user).id
		self.commit()
		
	def get_rooms(self):
		room_provider = RoomProvider.Instance(self.identifier)
		return room_provider.find_by_fqdn(self)
		
	def get_users(self):
		user_provider = RoomProvider.Instance(self.identifier)
		return user_provider.find_by_fqdn(self)
		
@LocalSingleton
class UserProvider(LocalSingletonBase):
	presences = {
		"login": 1,
		"disconnect": 2,
		"join": 3,
		"leave": 4
	}
	
	statuses = {
		"available": 1,
		"away": 2,
		"xa": 3,
		"dnd": 4,
		"chat": 5,
		"offline": 6
	}
	
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
	
	def normalize_jid(self, user, keep_resource=False):
		if user is None or user == "":
			return None
		elif isinstance(user, JID):
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
		
	def wrap(self, row):
		item = User(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="users")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such user(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, jid):
		component = Component.Instance(self.identifier)
		
		try:
			username, fqdn = self.normalize_jid(jid).split("@", 1)
		except ValueError, e:
			# No @ found, most likely a component name.
			raise NotFoundException("Not a known user, no @ found.")
			
		return self.get_from_query("SELECT * FROM users WHERE `Username` = ? AND `FqdnId` = ? LIMIT 1", (username, component.get_fqdn().id))[0]
		
	def find_by_email(self, email):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM users WHERE `EmailAddress` = ? AND `FqdnId` = ?", (email, component.get_fqdn().id))
		
	def find_by_nickname(self, nickname):
		component = Component.Instance(self.identifier)
		return self.get_from_query("SELECT * FROM users WHERE `Nickname` = ? AND `FqdnId` = ? LIMIT 1", (nickname, component.get_fqdn().id))[0]
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM users WHERE `Id` = ? AND `FqdnId` = ? LIMIT 1", (id_, component.get_fqdn().id))[0]
		
		return self.cache[id_]
		
	def find_by_fqdn(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		fqdn_id = fqdn_provider.normalize_fqdn(fqdn).id
		return self.get_from_query("SELECT * FROM users WHERE `FqdnId` = ?", (fqdn_id,))
		
	def status_string(self, value):
		reversed_statuses = dict(zip(self.statuses.values(), self.statuses.keys()))
		return reversed_statuses[value]
		
	def presence_string(self, value):
		reversed_presences = dict(zip(self.presences.values(), self.presences.keys()))
		return reversed_presences[value]
		
	def status_number(self, value):
		return self.statuses[value]
		
	def presence_number(self, value):
		return self.presences[value]
	
class User(object):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		user_provider = UserProvider.Instance(self.identifier)
		
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
		self.status = user_provider.status_string(row["Status"])
		self.status_message = row["StatusMessage"]
		
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
			
		self.commit()
		
	def get_affiliations(self, room=None):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		return affiliation_provider.get_user(self, room=room)
	
	def get_presences(self, room=None):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.get_user(self, room=room)
		
	def set_status(self, status):
		user_provider = UserProvider.Instance(self.identifier)
		self.row["Status"] = user_provider.status_number(status)
		self.commit()
		
	def set_presence(self, presence):
		user_provider = UserProvider.Instance(self.identifier)
		
		if presence == "disconnect":
			self.set_status("offline")
			
	def register_join(self, room, nickname, role):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.register_join(self, room, nickname, role)
			
	def register_leave(self, room):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.register_leave(self, room)
	
@LocalSingleton
class RoomProvider(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
	
	def normalize_jid(self, room):
		if room is None or room == "":
			return None
		elif isinstance(room, JID):
			return str(room.bare)
		else:
			# Probably a string, or coercible to one...
			return str(room)
			
	def normalize_room(self, room):
		if isinstance(room, Room):
			return room
		else:
			return self.get(room)
		
	def wrap(self, row):
		item = Room(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="rooms")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such room(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, jid):
		component = Component.Instance(self.identifier)
		roomname, fqdn = self.normalize_jid(jid).split("@", 1)
		return self.get_from_query("SELECT * FROM rooms WHERE `Node` = ? AND `FqdnId` = ? LIMIT 1", (roomname, component.get_fqdn().id))[0]
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM rooms WHERE `Id` = ? AND `FqdnId` = ? LIMIT 1", (id_, component.get_fqdn().id))[0]
		
		return self.cache[id_]
		
	def find_by_fqdn(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		fqdn_id = fqdn_provider.normalize_fqdn(fqdn).id
		return self.get_from_query("SELECT * FROM rooms WHERE `FqdnId` = ?", (fqdn_id,))
	
class Room(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"owner": self.get_owner,
			"fqdn": self.get_fqdn
		}
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		
		self.id = row["Id"]
		self.jid = "%s@conference.%s" % (row["Node"], fqdn_provider.find_by_id(row["FqdnId"]).fqdn)
		self._fqdn = row["FqdnId"]
		self.name = row["Name"]
		self.description = row["Description"]
		self._owner = row["OwnerId"]
		self.usercount = row["LastUserCount"]
		self.creation_date = row["CreationDate"]
		self.archival_date = row["ArchivalDate"]
		self.private = bool(row["IsPrivate"])
		self.archived = bool(row["IsArchived"])
		
	def get_owner(self):
		user_provider = UserProvider.Instance(self.identifier)
		return user_provider.find_by_id(self._owner)
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.find_by_id(self._fqdn)
		
	def increment_usercount(self, amount=1):
		self.row["LastUserCount"] = row["LastUserCount"] + amount
		self.commit()
		
	def decrement_usercount(self, amount=1):
		self.row["LastUserCount"] = row["LastUserCount"] + amount
		self.commit()
		
	def update_metadata(self, data):
		if "name" in data:
			self.row["Name"] = data["name"]
			
		if "description" in data:
			self.row["Description"] = data["description"]
			
		self.commit()
			
	def change_owner(self, user):
		user_provider = UserProvider.Instance(self.identifier)
		self.row["OwnerId"] = user_provider.normalize_user(user).id
		self.commit()
	
	def get_affiliations(self, user=None):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		return affiliation_provider.find_by_room(self, user=user)
	
	def get_presences(self, user=None):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.find_by_room(self, user=user)
	
	def register_join(self, user, nickname, role):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.register_join(user, self, nickname, role)
		
	def register_leave(self, user):
		presence_provider = PresenceProvider.Instance(self.identifier)
		return presence_provider.register_leave(user, self)
		
@LocalSingleton
class AffiliationProvider(LocalSingletonBase):
	affiliations = {
		"owner": 1,
		"admin": 2,
		"member": 3,
		"outcast": 4,
		"none": 5
	}
	
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
		
	def affiliation_string(self, value):
		reversed_affiliations = dict(zip(self.affiliations.values(), self.affiliations.keys()))
		return reversed_affiliations[value]
		
	def affiliation_number(self, value):
		return self.affiliations[value]
	
	def normalize_affiliation(self, affiliation):
		if isinstance(affiliation, Affiliation):
			return affiliation
		else:
			return self.find_by_id(affiliation)
		
	def wrap(self, row):
		item = Affiliation(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="affiliations")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such affiliation(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, room, user):
		return self.find_by_room_user(room, user)
		
	def find_by_room(self, room, user=None):
		room_provider = RoomProvider.Instance(self.identifier)
		
		room = room_provider.normalize_room(room)
		
		if user is None:
			return self.get_from_query("SELECT * FROM affiliations WHERE `RoomId` = ?", (room.id,))
		else:
			return self.find_by_room_user(room, user)
		
	def find_by_user(self, user, room=None):
		user_provider = UserProvider.Instance(self.identifier)
		
		user = user_provider.normalize_user(user)
		
		if room is None:
			return self.get_from_query("SELECT * FROM affiliations WHERE `UserId` = ?", (user.id,))
		else:
			return self.find_by_room_user(room, user)
		
	def find_by_room_user(self, room, user):
		room_provider = RoomProvider.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		room = room_provider.normalize_room(room)
		user = user_provider.normalize_user(user)
		
		return self.get_from_query("SELECT * FROM affiliations WHERE `RoomId` = ? AND `UserId` = ? LIMIT 1", (room.id, user.id))[0]
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM affiliations WHERE `Id` = ? AND `FqdnId` = ? LIMIT 1", (id_, component.get_fqdn().id))[0]
		
		return self.cache[id_]
		
	def find_by_fqdn(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		fqdn_id = fqdn_provider.normalize_fqdn(fqdn).id
		return self.get_from_query("SELECT * FROM affiliations WHERE `FqdnId` = ?", (fqdn_id,))
	
	def delete_from_cache(self, id_):
		del self.cache[id_]
	
class Affiliation(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"user": self.get_user,
			"room": self.get_room
		}
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		
		self.id = row["Id"]
		self._user = row["UserId"]
		self._room = row["RoomId"]
		self.affiliation = affiliation_provider.affiliation_string(row["Affiliation"])
		
	def get_user(self):
		user_provider = UserProvider.Instance(self.identifier)
		return user_provider.find_by_id(self._user)
	
	def get_room(self):
		room_provider = RoomProvider.Instance(self.identifier)
		return room_provider.find_by_id(self._room)
		
	def change(self, affiliation):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		self.row["Affiliation"] = affiliation_provider.affiliation_number(affiliation)
		self.commit()
		
	def delete(self):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		affiliation_provider.delete_from_cache(self.id)
		self.row.delete()
		
@LocalSingleton
class PresenceProvider(LocalSingletonBase):
	roles = {
		"moderator": 1,
		"none": 2,
		"participant": 3,
		"visitor": 4
	}
	
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
		
	def role_string(self, value):
		reversed_roles = dict(zip(self.roles.values(), self.roles.keys()))
		return reversed_roles[value]
		
	def role_number(self, value):
		return self.roles[value]
	
	def normalize_presence(self, presence):
		if isinstance(presence, Presence):
			return presence
		else:
			return self.find_by_id(presence)
		
	def wrap(self, row):
		item = Presence(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="presences")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such presence(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, room, nickname):
		room_provider = RoomProvider.Instance(self.identifier)
		room = room_provider.normalize_room(room)
		return self.get_from_query("SELECT * FROM presences WHERE `RoomId` = ? AND `Nickname` = ?", (room.id, nickname))
		
	def find_by_room(self, room, user=None):
		room_provider = RoomProvider.Instance(self.identifier)
		
		room = room_provider.normalize_room(room)
		
		if user is None:
			return self.get_from_query("SELECT * FROM presences WHERE `RoomId` = ?", (room.id,))
		else:
			return self.find_by_room_user(room, user)
		
	def find_by_user(self, user, room=None):
		user_provider = UserProvider.Instance(self.identifier)
		
		user = user_provider.normalize_user(user)
		
		if room is None:
			return self.get_from_query("SELECT * FROM presences WHERE `UserId` = ?", (user.id,))
		else:
			return self.find_by_room_user(room, user)
		
	def find_by_session(self, jid, room=None):
		user_provider = UserProvider.Instance(self.identifier)
		
		jid = JID(user_provider.normalize_jid(jid, keep_resource=True))
		user = user_provider.normalize_user(user)
		
		if room is None:
			return self.get_from_query("SELECT * FROM presences WHERE `UserId` = ? AND `Resource` = ?", (user.id, jid.resource))
		else:
			return self.find_by_room_user(room, user)
		
	def find_by_room_user(self, room, user):
		room_provider = RoomProvider.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		room = room_provider.normalize_room(room)
		user_jid = JID(user_provider.normalize_jid(jid, keep_resource=True))
		user = user_provider.normalize_user(user)
		
		return self.get_from_query("SELECT * FROM presences WHERE `RoomId` = ? AND `UserId` = ? AND `Resource` = ?", (room.id, user.id, user_jid.resource))
		
	def find_by_fqdn(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		fqdn_id = fqdn_provider.normalize_fqdn(fqdn).id
		return self.get_from_query("SELECT * FROM presences WHERE `FqdnId` = ?", (fqdn_id,))
	
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM presences WHERE `Id` = ? AND `FqdnId` = ? LIMIT 1", (id_, component.get_fqdn().id))[0]
		
		return self.cache[id_]
				
	def delete_from_cache(self, id_):
		del self.cache[id_]
		
	def register_join(self, user, room, nickname, role):
		user_provider = UserProvider.Instance(self.identifier)
		room_provider = RoomProvider.Instance(self.identifier)
		database = Database.Instance(self.identifier)
		
		user_jid = JID(user_provider.normalize_jid(user, keep_resource=True))
		bare_jid = user_provider.normalize_jid(user_jid)
		resource = user_jid.resource
		
		user_id = UserProvider.normalize_user(bare_jid).id
		room = RoomProvider.normalize_room(room)
		room_id = room.id
		fqdn_id = room.fqdn.id
		
		row = Row()
		row["UserId"] = user_id
		row["RoomId"] = room_id
		row["FqdnId"] = fqdn_id
		row["Nickname"] = nickname
		row["Role"] = self.role_number(role)
		row["Resource"] = resource
		database["presences"].append(row)
		
		return self.wrap(row)
		
	def register_leave(self, user, room):
		presence = self.find_by_room_user(room, user)
		presence.delete()
	
class Presence(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"user": self.get_user,
			"room": self.get_room,
			"fqdn": self.get_fqdn
		}
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		self.id = row["Id"]
		self._user = row["UserId"]
		self._room = row["RoomId"]
		self._fqdn = row["FqdnId"]
		self.resource = row["Resource"]
		self.nickname = row["Nickname"]
		self.role = presence_provider.role_string(row["Role"])
		
	def get_user(self):
		user_provider = UserProvider.Instance(self.identifier)
		return user_provider.find_by_id(self._user)
	
	def get_room(self):
		room_provider = RoomProvider.Instance(self.identifier)
		return room_provider.find_by_id(self._room)
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.find_by_id(self._fqdn)
		
	def change_role(self, role):
		presence_provider = PresenceProvider.Instance(self.identifier)
		self.row["Role"] = presence_provider.role_number(affiliation)
		self.commit()
		
	def delete(self):
		presence_provider = PresenceProvider.Instance(self.identifier)
		presence_provider.delete_from_cache(self.id)
		self.row.delete()
		
@LocalSingleton
class UserSettingProvider(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
		
	def normalize_setting(self, setting):
		if isinstance(setting, UserSetting):
			return setting
		else:
			return self.find_by_id(setting)
		
	def wrap(self, row):
		item = UserSetting(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="user_settings")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such setting(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, user, key, default=None):
		user_provider = UserProvider.Instance(self.identifier)
		user = user_provider.normalize_user(user)
		return self.get_from_query("SELECT * FROM user_settings WHERE `UserId` = ? AND `Key` = ? LIMIT 1", (user.id, key))[0]
		
	def find_by_user(self, user):
		user_provider = UserProvider.Instance(self.identifier)
		user = user_provider.normalize_user(user)
		return self.get_from_query("SELECT * FROM user_settings WHERE `UserId` = ?", (user.id,))
		
	def find_by_key(self, key):
		return self.get_from_query("SELECT * FROM user_settings WHERE `Key` = ?", (key,))
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM user_settings WHERE `Id` = ? LIMIT 1", (id_))[0]
		
		return self.cache[id_]
		
	def delete_from_cache(self, id_):
		del self.cache[id_]
		
class UserSetting(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"user": self.get_user
		}
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		self.id = row["Id"]
		self._user = row["UserId"]
		self.key = row["Key"]
		self.value = row["Value"]
		self.modified = row["LastModified"]
		
	def get_user(self):
		user_provider = UserProvider.Instance(self.identifier)
		return user_provider.find_by_id(self._user)
		
	def change(self, value):
		self.row["Value"] = value
		self.commit()
		
	def delete(self):
		usersetting_provider = UserSettingProvider.Instance(self.identifier)
		usersetting_provider.delete_from_cache(self.id)
		self.row.delete()
		
@LocalSingleton
class FqdnSettingProvider(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		self.cache = {}
		
	def normalize_setting(self, setting):
		if isinstance(setting, FqdnSetting):
			return setting
		else:
			return self.find_by_id(setting)
		
	def wrap(self, row):
		item = FqdnSetting(self.identifier, row)
		self.cache[row["Id"]] = item
		return item
		
	def get_from_query(self, query, params):
		database = Database.Instance(self.identifier)
		
		result = database.query(query, params, table="fqdn_settings")
		items = result.fetchall()
		
		if result is None:
			raise NotFoundException("No such setting(s) exist.")
		
		return [self.wrap(item) for item in items]
		
	def get(self, key):
		component = Component.Instance(self.identifier)
		return self.find_by_key(key, fqdn=component.get_fqdn().id)[0]
		
	def find_by_fqdn(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		
		fqdn = fqdn_provider.normalize_fqdn(fqdn)
		
		return self.get_from_query("SELECT * FROM fqdn_settings WHERE `FqdnId` = ? LIMIT 1", (fqdn.id,))[0]
		
	def find_by_key(self, key, fqdn=None):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		
		if fqdn is None:
			return self.get_from_query("SELECT * FROM fqdn_settings WHERE `Key` = ?", (key,))
		else:
			fqdn = fqdn_provider.normalize_fqdn(fqdn)
			return self.get_from_query("SELECT * FROM fqdn_settings WHERE `FqdnId` = ? AND `Key` = ?", (fqdn.id, key))
		
	def find_by_id(self, id_):
		component = Component.Instance(self.identifier)
		
		if id_ not in self.cache:
			self.cache[id_] = self.get_from_query("SELECT * FROM fqdn_settings WHERE `Id` = ? LIMIT 1", (id_))[0]
		
		return self.cache[id_]
		
	def delete_from_cache(self, id_):
		del self.cache[id_]
		
class FqdnSetting(LazyLoadingObject):
	def __init__(self, identifier, row):
		self.identifier = identifier
		self.row = row
		self.load_row(self.row)
		
		self.lazy_loaders = {
			"fqdn": self.get_fqdn
		}
		
	def commit(self):
		self.row.commit()
		self.load_row(self.row)
		
	def load_row(self, row):
		self.id = row["Id"]
		self._fqdn = row["FqdnId"]
		self.key = row["Key"]
		self.value = row["Value"]
		self.modified = row["LastModified"]
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.find_by_id(self._fqdn)
		
	def change(self, value):
		self.row["Value"] = value
		self.commit()
		
	def delete(self):
		usersetting_provider = UserSettingProvider.Instance(self.identifier)
		usersetting_provider.delete_from_cache(self.id)
		self.row.delete()

from .exceptions import NotFoundException, ConfigurationException
from .loggers import ApplicationLogger
from .db import Database, Row
from .component import Component

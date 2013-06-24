import logging, json, oursql, os
from datetime import datetime

from component import Component

def get_relative_path(path):
	my_path = os.path.dirname(os.path.abspath(__file__))
	return os.path.normpath(os.path.join(my_path, path))

class EnvoyComponent(Component):
	event_types = {
		"message": 1,
		"pm": 2,
		"status": 3,
		"presence": 4,
		"topic": 5
	}
	
	event_presences = {
		"login": 1,
		"disconnect": 2,
		"join": 3,
		"leave": 4
	}
	
	event_statuses = {
		"available": 1,
		"away": 2,
		"xa": 3,
		"dnd": 4,
		"chat": 5
	}
	
	def __init__(self, jid, host, port, password):
		Component.__init__(self, jid, host, port, password)
		
		# Hook events
		self.register_event("login", self.on_login)
		self.register_event("logout", self.on_logout)
		self.register_event("ping", self.on_ping)
		self.register_event("status", self.on_status)
		self.register_event("join", self.on_join)
		self.register_event("leave", self.on_leave)
		self.register_event("group_message", self.on_group_message)
		self.register_event("private_message", self.on_private_message)
		self.register_event("topic_change", self.on_topic_change)
		self.register_event("group_highlight", self.on_group_highlight)
		
		# Hook XEP-0045 presence tracking to use the Envoy database
		self['xep_0045'].api.register(self._envoy_is_joined_room, 'is_joined_room')
		self['xep_0045'].api.register(self._envoy_get_joined_rooms, 'get_joined_rooms')
		self['xep_0045'].api.register(self._envoy_add_joined_room, 'add_joined_room')
		self['xep_0045'].api.register(self._envoy_del_joined_room, 'del_joined_room')
		
		# TODO: Update internal user cache when vCard changes occur
		cursor = db.cursor()
		cursor.execute("SELECT Username, Fqdn, EmailAddress, FirstName, LastName, Nickname, JobTitle FROM users WHERE `Active` = 1")
		
		for row in cursor:
			jid = "%s@%s" % (row[0], row[1])
			email_address, first_name, last_name, nickname, job_title = row[2:]
			user = self._envoy_user_cache.get(jid)
			user.update_vcard({
				"email_address": email_address,
				"first_name": first_name,
				"last_name": last_name,
				"nickname": nickname,
				"job_title": job_title
			})
			
			logging.info("Found user %s in database with nickname @%s" % (jid, nickname))
			
		cursor.execute("SELECT UserJid, RoomJid FROM presences")
		
		for row in cursor:
			user, room = row
			self._envoy_user_cache.get(user.split("/", 1)[0]).add_room(room)
			
		for jid, user in self._envoy_user_cache.cache.iteritems():
			print user.jid, user.nickname, user.rooms
		
	def on_login(self, user):
		self._envoy_log_event(datetime.now(), user, "", self.event_types["presence"], self.event_presences["login"])
		print "%s just logged in." % user

	def on_logout(self, user, reason):
		self._envoy_log_event(datetime.now(), user, "", self.event_types["presence"], self.event_presences["disconnect"], reason)
		print "%s just disconnected with reason '%s'." % (user, reason)

	def on_ping(self, user):
		print "%s just pinged." % user

	def on_status(self, user, status, message):
		self._envoy_log_event(datetime.now(), user, "", self.event_types["status"], self.event_statuses[status], message)
		print "%s just changed their status to %s (%s)." % (user, status, message)

	def on_join(self, user, room):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["presence"], self.event_presences["join"])
		print "%s joined %s." % (user, room)

	def on_leave(self, user, room):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["presence"], self.event_presences["leave"])
		print "%s left %s." % (user, room)
		
	def on_group_message(self, user, room, body):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["message"], body)
		print "%s sent channel message to %s: '%s'" % (user, room, body)
		
	def on_private_message(self, sender, recipient, body):
		self._envoy_log_event(datetime.now(), sender, recipient, self.event_types["pm"], body)
		print "%s sent private message to %s: '%s'" % (sender, recipient, body)
	
	def on_group_highlight(self, sender, recipient, room, body):
		print "%s highlighted %s in %s in a channel message: %s" % (sender, recipient, room, body)
	
	def on_idle_private_message(self, sender, recipient, body):
		pass
		
	def on_idle_group_highlight(self, sender, recipient, body):
		pass
		
	def on_topic_change(self, user, room, topic):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["topic"], topic)
		print "%s changed topic for %s to '%s'" % (user, room, topic)
	
	# Envoy uses override methods for the user presence tracking feature in
	# the XEP-0045 plugin. Instead of storing the presences in memory, they
	# are stored in the Envoy database. This way, user presences are preserved 
	# across component restarts, thereby preventing inaccurate log entries.
	# Override methods are registered using SleekXMPPs API registry.
	
	def _envoy_is_joined_room(self, jid, node, ifrom, data):
		# Override for the _is_joined_room method.
		# Checks whether a JID was already present in a room.
		query = "SELECT COUNT(*) FROM presences WHERE `UserJid` = ? AND `RoomJid` = ?"
		cursor = db.cursor()
		cursor.execute(query, (str(jid), str(node)))
		return (cursor.fetchone()[0] > 0)
	
	def _envoy_get_joined_rooms(self, jid, node, ifrom, data):
		# Override for the _get_joined_rooms method.
		# Retrieves a list of all rooms a JID is present in.
		query = "SELECT * FROM presences WHERE `UserJid` = ?"
		cursor = db.cursor()
		cursor.execute(query, (str(jid)))
		return set([row[2] for row in cursor])
		
	def _envoy_add_joined_room(self, jid, node, ifrom, data):
		# Override for the _add_joined_room method.
		# Registers a JID presence in a room.
		query = "INSERT INTO presences (`UserJid`, `RoomJid`) VALUES (?, ?)"
		cursor = db.cursor()
		cursor.execute(query, (str(jid), str(node)))
		
	def _envoy_del_joined_room(self, jid, node, ifrom, data):
		# Override for the _del_joined_room method.
		# Removes a JID presence in a room.
		query = "DELETE FROM presences WHERE `UserJid` = ? AND `RoomJid` = ?"
		cursor = db.cursor()
		cursor.execute(query, (str(jid), str(node)))
		
	def _envoy_log_event(self, timestamp, sender, recipient, event_type, payload, extra=None):
		cursor = db.cursor()
		
		if event_type == 1 or event_type == 2 or event_type == 5:  # Message
			query = "INSERT INTO log_messages (`Date`, `Sender`, `Recipient`, `Type`, `Message`) VALUES (?, ?, ?, ?, ?)"
			cursor.execute(query, (timestamp, str(sender), str(recipient), event_type, payload))
		elif event_type == 3 or event_type == 4:  # Event
			if extra is None:
				extra = ""
			query = "INSERT INTO log_events (`Date`, `Sender`, `Recipient`, `Type`, `Event`, `Extra`) VALUES (?, ?, ?, ?, ?, ?)"
			cursor.execute(query, (timestamp, str(sender), str(recipient), event_type, payload, extra))
			

logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')

configuration = json.load(open(get_relative_path("../config.json"), "r"))

db = oursql.connect(host=configuration['database']['hostname'], user=configuration['database']['username'], 
                    passwd=configuration['database']['password'], db=configuration['database']['database'],
                    autoreconnect=True)

xmpp = EnvoyComponent("component.envoy.local", "envoy.local", 5347, "password")
xmpp.connect()
xmpp.process(block=True)

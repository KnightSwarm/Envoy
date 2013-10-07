import logging, json, oursql, os, copy, time
from datetime import datetime
from marrow.mailer import Message, Mailer

from twilio import TwilioRestException
from twilio.rest import TwilioRestClient

from component import Component
from util import state

from sleekxmpp.exceptions import IqError
from sleekxmpp.jid import JID

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
	
	def __init__(self, jid, host, port, password, conference_host):
		Component.__init__(self, jid, host, port, password, conference_host)
		
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
		self.register_event("presences_purged", self.on_presences_purged)
		
		# Hook XEP-0045 presence tracking to use the Envoy database
		self['xep_0045'].api.register(self._envoy_is_joined_room, 'is_joined_room')
		self['xep_0045'].api.register(self._envoy_get_joined_rooms, 'get_joined_rooms')
		self['xep_0045'].api.register(self._envoy_add_joined_room, 'add_joined_room')
		self['xep_0045'].api.register(self._envoy_del_joined_room, 'del_joined_room')
		
		# TODO: Update internal user cache when vCard changes occur
		cursor = database.query("SELECT * FROM users WHERE `Active` = 1")
		
		for row in cursor:
			jid = "%s@%s" % (row['Username'], row['Fqdn'])
			user = self._envoy_user_cache.get(jid)
			user.update_vcard({
				"email_address": row['EmailAddress'],
				"first_name": row['FirstName'],
				"last_name": row['LastName'],
				"nickname": row['Nickname'],
				"job_title": row['JobTitle'],
				"mobile_number": row['MobileNumber']
			})
			
			logging.info("Found user %s in database with nickname @%s" % (jid, row['Nickname']))
			
		cursor = database.query("SELECT * FROM presences")
		
		for row in cursor:
			# FIXME: Use SleekXMPPs JID parsing
			bare_jid, resource = row['UserJid'].split("/", 1)
			self._envoy_user_cache.get(bare_jid).add_room(row[RoomJid'], resource)
			
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

	def on_join(self, user, room, nickname):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["presence"], self.event_presences["join"])
		print "%s joined %s with nickname %s." % (user, room, nickname)

	def on_leave(self, user, room):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["presence"], self.event_presences["leave"])
		print "%s left %s." % (user, room)
		
	def on_group_message(self, user, room, body):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["message"], body)
		print "%s sent channel message to %s: '%s'" % (user, room, body)
		
	def on_private_message(self, sender, recipient, body):
		self._envoy_log_event(datetime.now(), sender, recipient, self.event_types["pm"], body)
		print "%s sent private message to %s: '%s'" % (sender, recipient, body)
		
		# We will only send a notification if the user is not using OTR. Sending encrypted gibberish
		# wouldn't make any sense.
		if not body.startswith("?OTR:"):
			self.notify_if_idle(sender, recipient.bare, "", body, "")
			
		# If development mode is turned on, and the message is directed at the component itself,
		# follow up on that.
		if configuration["development_mode"] == True:
			if recipient == self.boundjid:
				self.handle_development_command(sender, recipient, body)
	
	def on_group_highlight(self, sender, recipient, room, body, highlight):
		print "%s highlighted %s in %s in a channel message: %s (highlighted content is %s)" % (sender, recipient, room, body, highlight)
		self.notify_if_idle(sender, recipient, room, body, highlight)
	
	def on_topic_change(self, user, room, topic):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["topic"], topic)
		print "%s changed topic for %s to '%s'" % (user, room, topic)
	
	def on_presences_purged(self):
		# We'll build a local dict of all the current presences in the UserCache, that we can modify
		# in place later on.
		all_presences = {}
		
		for jid, user in self._envoy_user_cache.cache.iteritems():
			all_presences[jid] = copy.deepcopy(user.rooms)
			
		deletable_ids = []
			
		# During the first pass, we will retrieve all recorded presences from the database and
		# iterate through them. Every presence that also exists in the dict, will be removed from
		# the dict and left intact in the database. Every presence that doesn't exist in the dict,
		# will be removed from the database. After the first pass, the dict will only hold the
		# "missing" entries that are not in the database yet.
		
		cursor = database.query("SELECT * FROM presences")
		
		for row in cursor:
			room_jid = row['RoomJid']
			# FIXME: Use SleekXMPP's JID parsing
			user_bare, user_resource = row['UserJid'].split("/")
			
			try:
				if user_resource in all_presences[user_bare][room_jid]:
					# FIXME: This can probably be optimized for speed by keeping a separate list of to-be-deleted resources
					#        and recreating the resource list in one pass.
					all_presences[user_bare][room_jid] = [x for x in all_presences[user_bare][room_jid] if x != user_resource]
				else:
					deletable_ids.append(row['Id'])
			except KeyError, e:
				deletable_ids.append(row['Id'])
		
		# Before doing actual database insertion, we'll want to clean up empty entries.
		for user in all_presences.keys():
			for room in all_presences[user].keys():
				if len(all_presences[user][room]) == 0:
					del all_presences[user][room]
			
			if len(all_presences[user]) == 0:
				del all_presences[user]
				
		logging.info("Deletable presence IDs: %s" % deletable_ids)
		logging.info("Remaining presences for database insertion: %s" % all_presences)
		
		for id_ in deletable_ids:
			database.query("DELETE FROM `presences` WHERE `Id` = ?", (id_,))
			
		for user, rooms in all_presences.iteritems():
			for room, resources in rooms.iteritems():
				for resource in resources:
					database.query("INSERT INTO presences (`UserJid`, `RoomJid`) VALUES (?, ?)", ("%s/%s" % (user, resource), room))
					
		# We manually commit, for performance reasons
		database.commit()
		
		for jid, user in self._envoy_user_cache.cache.iteritems():
			logging.debug("Room presence list AFTER database sync for user %s: %s" % (jid, user.rooms))
		
		logging.info("Synchronized database with UserCache.")
	
	def notify_if_idle(self, sender, recipient, room, body, highlight):
		# We should only send a notification if we can reasonable assume that the user is not paying
		# attention to their client. If they are away, extended away, or offline (unavailable), they
		# will be sent an external notification. When a user is automatically marked idle by their
		# client for lack of interaction, they will turn to an 'away' or 'extended away' state - we
		# don't need to handle this separately.
		if self._envoy_user_cache.get(recipient).presence in [state.AWAY, state.XA, state.UNAVAILABLE, state.DND]:
			self.notify(sender, recipient, room, body, highlight)
		elif self._envoy_user_cache.get(recipient).presence == state.UNKNOWN:
			# FIXME: Fetch the correct state?
			logging.error("Unknown state detected for user %s" % recipient)
		
	def notify(self, sender, recipient, room, body, highlight):
		# We don't want to send external notifications if the user state is set to Do Not Disturb,
		# unless the settings for the user explicitly indicate that this is okay..
		if self._envoy_user_cache.get(recipient).presence != state.DND or self.get_user_setting(recipient, "notify_on_dnd", "0") == "1":
			# Actually send a notification. We can use the phone number and e-mail address from
			# their vCard information (in the user cache) to do so.
			is_private = (room == "")
			sender_name = self._envoy_user_cache.get(sender.bare).full_name
			
			# We'll start out with an SMS
			sms_recipient = self._envoy_user_cache.get(recipient).mobile_number
			
			if sms_recipient != "":
				if is_private:
					sms_prefix = "PM from %s: " % sender_name
				else:
					# FIXME: Use human-readable room name rather than JID
					if highlight == "all":
						sms_prefix = "@all in %s: [%s] " % (room.node, sender_name)
					else:
						sms_prefix = "Highlight in %s: [%s] " % (room.node, sender_name)
				
				# An SMS message can be at most 60 characters
				sms_maxlen = 160 - len(sms_prefix)
				
				if len(body) > sms_maxlen:
					# We need 3 characters for the ellipsis
					sms_bodylen = sms_maxlen - 3
					sms_body = "%s..." % body[:sms_bodylen]
				else:
					sms_body = body
					
				sms_body = sms_prefix + sms_body
				
				try:
					try:
						send_sms = (configuration["mock"]["sms"] == False)
					except KeyError, e:
						send_sms = True
						
					if send_sms:
						message = twilio_client.sms.messages.create(body=sms_body, to=sms_recipient, from_=configuration['twilio']['sender'])
						logging.info("SMS sent to %s: %s" % (sms_recipient, sms_body))
					else:
						logging.info("Pretending to send SMS to %s: %s" % (sms_recipient, sms_body))
				except TwilioRestException, e:
					logging.error("An error occurred during sending of an SMS to %s: %s" % (sms_recipient, repr(e)))
			else:
				logging.debug("Not sending an SMS to %s, because no mobile number is configured." % recipient)
			
			email_recipient = self._envoy_user_cache.get(recipient).email_address
			
			# Now let's send emails.
			# TODO: Add fancy HTML e-mails.
			recipient_name = self._envoy_user_cache.get(recipient).first_name
			
			if is_private:
				template_file = open("templates/pm.txt")
				template = template_file.read()
				template_file.close()
				
				subject = "%s sent you a private message" % (sender_name)
				email_body = template.format(first_name=recipient_name, sender=sender_name, message=body)
			else:
				template_file = open("templates/highlight.txt")
				template = template_file.read()
				template_file.close()
				
				subject = "%s mentioned you in the room %s" % (sender_name, room.node)
				email_body = template.format(first_name=recipient_name, sender=sender_name, room=room.node, message=body)
			
			try:
				send_email = (configuration["mock"]["email"] == False)
			except KeyError, e:
				send_email = True
				
			if send_email:
				self.send_email([(email_recipient, subject, email_body)])
			else:
				logging.info("Pretending to send e-mail to %s: %s" % (email_recipient, email_body))
	
	def send_email(self, emails):
		# FIXME: Deal properly with older SMTP implementations that only support SSL and not STARTTLS.
		mailer = Mailer({
			"manager.use": "immediate",
			"transport.use": "smtp",
			"transport.host": configuration['smtp']['hostname'],
			"transport.port": configuration['smtp']['port'],
			"transport.tls": configuration['smtp']['tls'],
			"transport.username": configuration['smtp']['username'],
			"transport.password": configuration['smtp']['password'],
			"transport.max_messages_per_connection": 5
		})
		
		mailer.start()

		# FIXME: Exceptions when the below key doesn't exist, are silently eaten?
		sender = configuration['smtp']['sender']
		
		for email in emails:
			try:
				recipient, subject, body = email
				
				message = Message(author=sender, to=recipient, subject=subject, plain=body)
				mailer.send(message)
				logging.info("E-mail sent to %s: %s" % (recipient, body))
			except Exception, e:
				logging.error("An error occurred during sending of an e-mail to %s: %s" % (recipient, repr(e)))
			
		mailer.stop()
	
	def handle_development_command(self, sender, recipient, body):
		if body.startswith("$"):
			try:
				output = eval(body[1:].strip(), {"self": self})
				self.send_message(mto=sender, mbody=unicode(output))
			except IqError, e:
				logging.error("IqError: %s" % e.iq)
		elif body == "purge":
			self._envoy_purge_presences()
		elif body == "debugtree":
			self.send_message(mto=sender, mbody=self._envoy_user_cache.get_debug_tree())
	
	def get_user_id(self, username, fqdn):
		cursor = database.query("SELECT * FROM users WHERE `Username` = ? AND `Fqdn` = ? LIMIT 1", (username, fqdn))
		row = cursor.fetchone()
		
		if row is None:
			raise Exception("No such user exists.")
			
		return row['Id']
	
	def get_user_setting(self, jid, key, default=""):
		username, fqdn = JID(jid).bare.split("@")
		user_id = self.get_user_id(username, fqdn)
		
		database.query("SELECT * FROM user_settings WHERE `UserId` = ? AND `Key` = ? LIMIT 1", (user_id, key))
		row = cursor.fetchone()
		
		if row is None:
			return default
			
		return row['Value']
		
		
	def set_user_setting(self, jid, key, value):
		username, fqdn = JID(jid).bare.split("@")
		user_id = self.get_user_id(username, fqdn)
		current_timestamp = datetime.utcnow()
		
		cursor = database.query("UPDATE user_settings SET `Value` = ?, `LastModified` = ? WHERE `UserId` = ? AND `Key` = ?", (value, current_timestamp, user_id, key), commit=True)
		
		if cursor.rowcount == 0:
			# The entry didn't exist yet... insert a new one
			row = db.Row()
			row['Value'] = value
			row['LastModified'] = current_timestamp
			row['UserId'] = user_id
			row['Key'] = key
			database['user_settings'].append(row)
	
	# Envoy uses override methods for the user presence tracking feature in
	# the XEP-0045 plugin. Instead of storing the presences in memory, they
	# are stored in the Envoy database. This way, user presences are preserved 
	# across component restarts, thereby preventing inaccurate log entries.
	# Override methods are registered using SleekXMPPs API registry.
	
	def _envoy_is_joined_room(self, jid, node, ifrom, data):
		# Override for the _is_joined_room method.
		# Checks whether a JID was already present in a room.
		cursor = database.query("SELECT COUNT(*) FROM presences WHERE `UserJid` = ? AND `RoomJid` = ?", (str(jid), str(node)))
		return (cursor.fetchone()['COUNT(*)'] > 0)
	
	def _envoy_get_joined_rooms(self, jid, node, ifrom, data):
		# Override for the _get_joined_rooms method.
		# Retrieves a list of all rooms a JID is present in.
		cursor = database.query("SELECT * FROM presences WHERE `UserJid` = ?", (str(jid),)))
		return set([row['RoomJid'] for row in cursor])
		
	def _envoy_add_joined_room(self, jid, node, ifrom, data):
		# Override for the _add_joined_room method.
		# Registers a JID presence in a room.
		database.query("INSERT INTO presences (`UserJid`, `RoomJid`) VALUES (?, ?)", (str(jid), str(node)))
		
	def _envoy_del_joined_room(self, jid, node, ifrom, data):
		# Override for the _del_joined_room method.
		# Removes a JID presence in a room.
		database.query("DELETE FROM presences WHERE `UserJid` = ? AND `RoomJid` = ?", (str(jid), str(node)))
		
	def _envoy_log_event(self, timestamp, sender, recipient, event_type, payload, extra=None):
		cursor = db.cursor()
		
		if event_type == 1 or event_type == 2 or event_type == 5:  # Message
			row = db.Row()
			row['Date'] = timestamp
			row['Sender'] = str(sender)
			row['Recipient'] = str(recipient)
			row['Type'] = event_type
			row['Message'] = payload
			database['log_messages'].append(row)
		elif event_type == 3 or event_type == 4:  # Event
			if extra is None:
				extra = ""
				
			row = db.Row()
			row['Date'] = timestamp
			row['Sender'] = str(sender)
			row['Recipient'] = str(recipient)
			row['Type'] = event_type
			row['Event'] = payload
			row['Extra'] = extra
			database['log_events'].append(row)
			

logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')

configuration = json.load(open(get_relative_path("../config.json"), "r"))

#db = oursql.connect(host=configuration['database']['hostname'], user=configuration['database']['username'], 
#                    passwd=configuration['database']['password'], db=configuration['database']['database'],
#                    autoreconnect=True)
database = db.Database(configuration['database']['hostname'], configuration['database']['username'], 
                       configuration['database']['password'], configuration['database']['database'])

try:
	sms_enabled = (configuration['mock']['sms'] == False)
except KeyError, e:
	sms_enabled = True

if sms_enabled == True:
	# If mock mode is turned on for SMS, we don't need to send actual API requests, so configuration is also not necessary.
	twilio_client = TwilioRestClient(configuration['twilio']['sid'], configuration['twilio']['token'])

xmpp = EnvoyComponent("component.envoy.local", "127.0.0.1", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)

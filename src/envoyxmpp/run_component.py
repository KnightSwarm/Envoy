import logging, json, oursql, os, smtplib
from datetime import datetime
from email.mime.text import MIMEText

from twilio import TwilioRestException
from twilio.rest import TwilioRestClient

from component import Component
from util import state

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
		cursor.execute("SELECT Username, Fqdn, EmailAddress, FirstName, LastName, Nickname, JobTitle, MobileNumber FROM users WHERE `Active` = 1")
		
		for row in cursor:
			jid = "%s@%s" % (row[0], row[1])
			email_address, first_name, last_name, nickname, job_title, mobile_number = row[2:]
			user = self._envoy_user_cache.get(jid)
			user.update_vcard({
				"email_address": email_address,
				"first_name": first_name,
				"last_name": last_name,
				"nickname": nickname,
				"job_title": job_title,
				"mobile_number": mobile_number
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
	
	def on_group_highlight(self, sender, recipient, room, body, highlight):
		print "%s highlighted %s in %s in a channel message: %s (highlighted content is %s)" % (sender, recipient, room, body, highlight)
		self.notify_if_idle(sender, recipient, room, body, highlight)
	
	def on_topic_change(self, user, room, topic):
		self._envoy_log_event(datetime.now(), user, room, self.event_types["topic"], topic)
		print "%s changed topic for %s to '%s'" % (user, room, topic)
	
	def notify_if_idle(self, sender, recipient, room, body, highlight):
		# We should only send a notification if we can reasonable assume that the user is not paying
		# attention to their client. If they are away, extended away, or offline (unavailable), they
		# will be sent an external notification. When a user is automatically marked idle by their
		# client for lack of interaction, they will turn to an 'away' or 'extended away' state - we
		# don't need to handle this separately.
		if self._envoy_user_cache.get(recipient).presence in [state.AWAY, state.XA, state.UNAVAILABLE]:
			self.notify(sender, recipient, room, body, highlight)
		elif self._envoy_user_cache.get(recipient).presence == state.UNKNOWN:
			# FIXME: Fetch the correct state?
			logging.error("Unknown state detected for user %s" % recipient)
		
	def notify(self, sender, recipient, room, body, highlight):
		# We never want to send external notifications if the user state is set to Do Not Disturb.
		if self._envoy_user_cache.get(recipient).presence != state.DND:
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
					message = twilio_client.sms.messages.create(body=sms_body, to=sms_recipient, from_=configuration['twilio']['sender'])
					logging.info("SMS sent to %s." % sms_recipient)
				except TwilioRestException, e:
					logging.error("An error occurred during sending of an SMS to %s: %s" % (sms_recipient, repr(e)))
			else:
				logging.debug("Not sending an SMS to %s, because no mobile number is configured." % recipient)
			
			email_recipient = self._envoy_user_cache.get(recipient).email_address
			
			# Now let's send emails.
			self.send_email([(email_recipient, "Notification in Envoy", "%s highlighted you: %s" % (sender_name, body))])
	
	def send_email(self, emails):
		# FIXME: Deal properly with older SMTP implementations that only support SSL and not STARTTLS.
		session = smtplib.SMTP(configuration['smtp']['host'], configuration['smtp']['port'])
		session.ehlo()
		
		# If the configuration indicates the use of TLS, we will issue a STARTTLS
		# command, and send another EHLO.
		try:
			if configuration['smtp']['tls'] == True:
				session.starttls()
				session.ehlo()
		except KeyError, e:
			pass
			
		session.login(configuration['smtp']['username'], configuration['smtp']['password'])
		
		# FIXME: Exceptions when the below key doesn't exist, are silently eaten?
		sender = configuration['smtp']['sender']
		
		for email in emails:
			try:
				recipient, subject, body = email
				
				message = MIMEText(body)
				message['Subject'] = subject
				message['From'] = sender
				message['To'] = recipient
				
				# FIXME: This doesn't work, for unclear reasons.
				print session.sendmail(sender, recipient, message.as_string())
				logging.info("E-mail sent to %s." % recipient)
			except Exception, e:
				logging.error("An error occurred during sending of an e-mail to %s: %s" % (recipient, repr(e)))
			
		session.quit()
	
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
			

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

configuration = json.load(open(get_relative_path("../config.json"), "r"))

db = oursql.connect(host=configuration['database']['hostname'], user=configuration['database']['username'], 
                    passwd=configuration['database']['password'], db=configuration['database']['database'],
                    autoreconnect=True)

twilio_client = TwilioRestClient(configuration['twilio']['sid'], configuration['twilio']['token'])

xmpp = EnvoyComponent("component.envoy.local", "127.0.0.1", 5347, "password")
xmpp.connect()
xmpp.process(block=True)

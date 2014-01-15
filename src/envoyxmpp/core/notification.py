from .util import LocalSingleton, LocalSingletonBase

from .providers import ConfigurationProvider, UserProvider, RoomProvider
from .notify import SmsSender, EmailSender

from sleekxmpp.jid import JID

@LocalSingleton
class HighlightChecker(LocalSingletonBase):
	def check(self, stanza):
		# FIXME: find_by methods need changing and error handling
		notifier = Notifier.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		room = stanza['to'].bare
		sender = stanza["from"].bare
		body = stanza["body"]
		
		highlights = re.findall("@([a-zA-Z0-9._-]+)", stanza["body"])
		for highlight in highlights:
			if highlight == "all":
				# Highlight everyone in the room
				affected = set(user_provider.find_by_room_presence(room) + user_provider.find_by_room_membership(room))
				
				for user in affected:
					if str(user.jid) != str(sender):
						notifier.notify_if_idle(sender, JID(user.jid), JID(room), body, highlight)
			else:
				# Highlight one particular nickname
				affected = set(user_provider.find_by_nickname(highlight))
				
				for user in affected:
					if user.in_room(room):
						notifier.notify_if_idle(sender, JID(user.jid), JID(room), body, highlight)
	
@LocalSingleton
class Notifier(LocalSingletonBase):
	def notify_if_idle(self, sender, recipient, room, body, highlight):
		cache = UserProvider.Instance(self.identifier)
		user = cache.get(recipient)
		
		if user.presence in (state.AWAY, state.XA, state.UNAVAILABLE, state.DND):
			self.notify(sender, recipient, room, body, highlight)
		elif user.presence == state.UNKNOWN:
			logging.warn("Unknown state detected for user %s" % recipient)
			user.update_presence()
		
	def notify(self, sender, recipient, room, body, highlight):
		# FIXME: Check DND!
		if room == "":
			self.notify_private_message(sender, recipient, body)
		else:
			self.notify_highlight(sender, recipient, room, body, highlight)
		
	def notify_highlight(self, sender, recipient, room, body, highlight):
		sms_sender = SmsSender.Instance(self.identifier)
		email_sender = EmailSender.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		room_provider = RoomProvider.Instance(self.identifier)
		
		sending_user = user_provider.get(sender)
		receiving_user = user_provider.get(recipient)
		room_data = room_provider.get(room)
		
		if receiving_user.phone_number != "":
			if highlight == "all":
				prefix = "@all in %s: " % room
			else:
				prefix = "Highlight in %s: " % room
			
			sms_sender.send(receiving_user.phone_number, prefix + body)
			
		if receiving_user.email_address != "":
			with open("templates/highlight.txt", "r") as template_file:
				template = template_file.read()
			
			email_body = template.format(first_name=receiving_user.first_name, sender=sending_user.full_name, room=room_data.name, message=body)
			subject = "%s mentioned you in the room %s" % (sender_name, room_name)
			
			email_sender.send(receiving_user.email_address, subject, email_body)
		
	def notify_private_message(self, sender, recipient, body):
		sms_sender = SmsSender.Instance(self.identifier)
		email_sender = EmailSender.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		sending_user = user_provider.get(sender)
		receiving_user = user_provider.get(recipient)
		
		if receiving_user.phone_number != "":
			if highlight == "all":
				prefix = "@all in %s: " % room
			else:
				prefix = "Highlight in %s: " % room
			
			sms_sender.send(receiving_user.phone_number, prefix + body)
			
		if user.email_address != "":
			with open("templates/pm.txt", "r") as template_file:
				template = template_file.read()
			
			email_body = template.format(first_name=receiving_user.first_name, sender=sending_user.full_name, message=body)
			subject = "%s sent you a private message" % (sender_name)
			
			email_sender.send(receiving_user.email_address, subject, email_body)
	
@LocalSingleton
class EmailSender(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		
		configuration = ConfigurationProvider.Instance(self.identifier)
		
		# FIXME: Deal properly with older SMTP implementations that only support SSL and not STARTTLS.
		self.mailer = Mailer({
			"manager.use": "immediate",
			"transport.use": "smtp",
			"transport.host": configuration.smtp_hostname,
			"transport.port": configuration.smtp_port,
			"transport.tls": configuration.smtp_tls,
			"transport.username": configuration.smtp_username,
			"transport.password": configuration.smtp_password,
			"transport.max_messages_per_connection": 5
		})
		
	def send(self, recipient, subject, body):
		# FIXME: Mock config!
		self.mailer.start()
		
		try:
			message = Message(author=configuration.smtp_sender, to=recipient, subject=subject, plain=body)
			self.mailer.send(message)
			logging.info("E-mail sent to %s: %s" % (recipient, body))
		except Exception, e:
			logging.error("An error occurred during sending of an e-mail to %s: %s" % (recipient, repr(e)))
		
		self.mailer.stop()
	
@LocalSingleton
class SmsSender(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		
		configuration = ConfigurationProvider.Instance(self.identifier)
			
		if configuration.mock_sms == False:
			self.client = TwilioRestClient(configuration.twilio_sid, configuration.twilio_token)
	
	def send(self, recipient, body):
		configuration = ConfigurationProvider.Instance(self.identifier)
			
		if configuration.mock_sms == False:
			message = self.client.sms.messages.create(body=self.cut_body(body), to=recipient, from_=configuration.twilio_sender)
			logging.info("SMS sent to %s: %s" % (recipient, body))
		else:
			logging.info("Pretending to send SMS to %s: %s" % (recipient, body))
			
	def cut_body(self, body):
		# An SMS message can be at most 160 characters
		if len(body) > 160:
			return body[:157] + "..."
		else:
			return body

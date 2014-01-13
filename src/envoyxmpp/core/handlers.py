from .util import Singleton, LocalSingleton, LocalSingletonBase
from .notification import HighlightChecker
from .cache import UserCache

@LocalSingleton
class StanzaHandler(LocalSingletonBase):	
	def process(self, stanza):
		stanza = wrapper['forwarded']['stanza']
		
		if isinstance(stanza, Iq):
			IqHandler.Instance(self.identifier).process(stanza)
		elif isinstance(stanza, Message):
			MessageHandler.Instance(self.identifier).process(stanza)
		elif isinstance(stanza, Presence):
			PresenceHandler.Instance(self.identifier).process(stanza)
		else:
			logging.warn("Unknown stanza type encountered: %s" % repr(stanza))

@LocalSingleton
class MessageHandler(LocalSingletonBase):
	def process(self, stanza):
		if stanza.match('message@type=groupchat/body'):
			self.group_message(stanza)
		elif stanza.match('message@type=groupchat/subject'):
			self.topic_change(stanza)
		elif stanza.match('message@type=chat/body'):
			self.private_message(stanza)
	
	def group_message(self, stanza):
		room = stanza["to"].bare
		user = stanza["from"].bare
		body = stanza["body"]
		
		UserCache.Instance(self.identifier).touch(user) # FIXME: Remove
		HighlightChecker.Instance(self.identifier).check(stanza)
		EventLogger.Instance(self.identifier).log_message(user, room, "message", body)
		
	def private_message(self, stanza):
		sender = stanza["from"].bare
		recipient = stanza["to"].bare
		body = stanza["body"]
		
		UserCache.Instance(self.identifier).touch(sender) # FIXME: Remove
		UserCache.Instance(self.identifier).touch(recipient) # FIXME: Remove
		EventLogger.Instance(self.identifier).log_message(sender, recipient, "pm", body)
	
	def topic_change(self, stanza):
		room = stanza['to'].bare
		user = stanza["from"].bare
		topic = stanza["subject"]
		
		UserCache.Instance(self.identifier).touch(user) # FIXME: Remove
		EventLogger.Instance(self.identifier).log_event(user, room, "topic"
	
@LocalSingleton	
class IqHandler(LocalSingletonBase):
	def process(self, stanza):
		logger = EventLogger.Instance(self.identifier)
		
		# In case it's necessary, the XPath for a ping is {jabber:client}iq/{urn:xmpp:ping}ping
		if MatchXPath("{jabber:client}iq/{urn:ietf:params:xml:ns:xmpp-session}session").match(stanza):
			# User logged in
			user = stanza["from"]
			
			logger.log_event(user, None, "presence", "login")
		
@LocalSingleton	
class PresenceHandler(LocalSingletonBase):
	def process(self, stanza):
		component = Component.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		logger = EventLogger.Instance(self.identifier)
		
		if stanza.match("presence/muc"):
			# MUC presence
			component['xep_0045']._handle_presence(stanza)
		else:
			sender = stanza["from"]
			recipient = stanza["to"]
			type_ = stanza["type"]
			message = stanza["status"]
			
			if recipient == "": # Ignore propagated presences
				user_provider.get(sender).set_status(type_)
				 
				if type_ == "available" or type_ in Presence.showtypes:
					logger.log_event(sender, "", "status", type_, message)
				elif type_ == "unavailable":
					logger.log_event(sender, "", "presence", "disconnect", message)
				
@LocalSingleton
class MucHandler(LocalSingletonBase):
	def process_join(self, stanza):
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		room = stanza["from"].bare
		nickname = stanza["from"].resource
		role = stanza["muc"]["role"]
		
		presence_provider.register_join(user, room, nickname, role)
		
	def process_leave(self, stanza):
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		room = stanza["from"].bare
		
		presence_provider.register_leave(user, room)
		
	def process_presence(self, stanza):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		room = stanza["from"].bare
		user = stanza["muc"]["jid"]
		affiliation = stanza["muc"]["affiliation"]
		role = stanza["muc"]["role"]
		
		if str(user) != "": # This might now throw a KeyError instead, since SleekXMPP changes
			affiliation_object = affiliation_provider.find_by_room_user(room, user)
			
			if affiliation_object.affiliation != affiliation:
				# EVENT: Affiliation change
				affiliation_object.change(affiliation)
			
			presence_object = presence_provider.find_by_room_user(room, user)
			
			if presence_object.role != role:
				# EVENT: Role change
				presence_object.change_role(role)
		else:
			pass # FIXME: Log warning, no valid JID found

@LocalSingleton
class DevelopmentCommandHandler(LocalSingletonBase):
	def process(self, stanza):
		# FIXME: Check dev mode!
		message_sender = MessageSender.Instance(self.identifier)
		
		sender = stanza["from"]
		recipient = stanza["to"]
		body = stanza["body"]
		
		if body.startswith("$"):
			handler = EvalHandler.Instance(self.identifier)
			handler.process(stanza)
		elif body == "purge":
			pass # FIXME: We might not need this anymore.
		elif body == "debugtree":
			builder = DebugTreeBuilder.Instance(self.identifier)
			message_sender.send(recipient=sender, body=builder.build())
			
@LocalSingleton
class EvalHandler(LocalSingletonBase):
	def process(self, stanza):
		message_sender = MessageSender.Instance(self.identifier)
		
		sender = stanza["from"]
		recipient = stanza["to"]
		body = stanza["body"]
		code = body[1:].strip()
		
		try:
			scope = {"self": self}
			scope.update(globals())
			output = eval(code, scope)
			message_sender.send(recipient=sender, body=unicode(output))
		except IqError, e:
			message_sender.send(recipient=sender, body=unicode("IqError encountered\n%s" % traceback.format_exc()))
			logging.error("IqError: %s" % e.iq)
		except:
			message_sender.send(recipient=sender, body=unicode("Uncaught exception encountered:\n%s" % traceback.format_exc()))

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
		room = stanza['to'].bare
		user = stanza["from"].bare
		
		UserCache.Instance(self.identifier).touch(user)
		HighlightChecker.Instance(self.identifier).check(stanza)
		
	def private_message(self, stanza):
		sender = stanza["from"].bare
		recipient = stanza["to"].bare
		
		UserCache.Instance(self.identifier).touch(sender)
		UserCache.Instance(self.identifier).touch(recipient)
	
	def topic_change(self, stanza):
		room = stanza['to'].bare
		user = stanza["from"].bare
		
		UserCache.Instance(self.identifier).touch(user)

@LocalSingleton
class DevelopmentCommandHandler(LocalSingletonBase):
	def process(self, stanza):
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

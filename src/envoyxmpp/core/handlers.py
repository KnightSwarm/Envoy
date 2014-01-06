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

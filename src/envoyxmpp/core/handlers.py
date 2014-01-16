from .util import Singleton, LocalSingleton, LocalSingletonBase

from sleekxmpp.stanza import Presence

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
		# EVENT: Group/room message received
		room = stanza["to"].bare
		user = stanza["from"].bare
		body = stanza["body"]
		
		HighlightChecker.Instance(self.identifier).check(stanza)
		EventLogger.Instance(self.identifier).log_message(user, room, "message", body)
		
	def private_message(self, stanza):
		# EVENT: Private message received
		sender = stanza["from"].bare
		recipient = stanza["to"].bare
		body = stanza["body"]
		
		EventLogger.Instance(self.identifier).log_message(sender, recipient, "pm", body)
	
	def topic_change(self, stanza):
		# EVENT: Topic changed
		room = stanza['to'].bare
		user = stanza["from"].bare
		topic = stanza["subject"]
		
		EventLogger.Instance(self.identifier).log_event(user, room, "topic", topic)
	
@LocalSingleton	
class IqHandler(LocalSingletonBase):
	def process(self, stanza):
		logger = EventLogger.Instance(self.identifier)
		
		# In case it's necessary, the XPath for a ping is {jabber:client}iq/{urn:xmpp:ping}ping
		if MatchXPath("{jabber:client}iq/{urn:ietf:params:xml:ns:xmpp-session}session").match(stanza):
			# EVENT: User logged in
			user = stanza["from"]
			
			logger.log_event(user, None, "presence", "login")
		
@LocalSingleton	
class PresenceHandler(LocalSingletonBase):
	def process(self, stanza):
		component = Component.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		logger = EventLogger.Instance(self.identifier)
		
		if stanza.match("presence/muc"):
			# EVENT: MUC presence
			component['xep_0045']._handle_presence(stanza)
		else:
			sender = stanza["from"]
			recipient = stanza["to"]
			type_ = stanza["type"]
			message = stanza["status"]
			
			if recipient == "": # Ignore propagated presences
				user_provider.get(sender).set_status(type_)
				 
				if type_ == "available" or type_ in Presence.showtypes:
					# EVENT: User status changed
					logger.log_event(sender, "", "status", type_, message)
				elif type_ == "unavailable":
					# EVENT: User logged out
					logger.log_event(sender, "", "presence", "disconnect", message)
				
@LocalSingleton
class MucHandler(LocalSingletonBase):
	def process_join(self, stanza):
		# EVENT: User joined room
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		room = stanza["from"].bare
		nickname = stanza["from"].resource
		role = stanza["muc"]["role"]
		
		presence_provider.register_join(user, room, nickname, role) # TODO: This might be better in a separate handler
		
	def process_leave(self, stanza):
		# EVENT: User left room
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		room = stanza["from"].bare
		
		presence_provider.register_leave(user, room) # TODO: This might be better in a separate handler
		
	def process_presence(self, stanza):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		room = stanza["from"].bare
		affiliation = stanza["muc"]["affiliation"]
		role = stanza["muc"]["role"]
		
		try:
			user = stanza["muc"]["jid"]
		except KeyError, e:
			return # No JID present
				
		if str(user) != "":
			affiliation_object = affiliation_provider.find_by_room_user(room, user)
			
			if affiliation_object.affiliation != affiliation:
				# EVENT: Affiliation change
				affiliation_object.change(affiliation)
			
			presence_object = presence_provider.find_by_room_user(room, user)
			
			if presence_object.role != role:
				# EVENT: Role change
				presence_object.change_role(role)
		else:
			logger = ApplicationLogger.Instance(self.identifier)
			logger.warning("No valid JID found in presence stanza! Stanza was %s" % stanza)

@LocalSingleton
class DevelopmentCommandHandler(LocalSingletonBase):
	# TODO: Make code actually use this...
	
	def process(self, stanza):
		configuration = ConfigurationProvider.Instance(self.identifier)
		#message_sender = MessageSender.Instance(self.identifier)
		
		if configuration.development_mode == True:
			sender = stanza["from"]
			recipient = stanza["to"]
			body = stanza["body"]
			
			if body.startswith("$"):
				handler = EvalHandler.Instance(self.identifier)
				handler.process(stanza)
			elif body == "sync":
				# EVENT: (Dev) sync command
				affiliation_syncer = AffiliationSyncer.Instance(self.identifier)
				presence_syncer = PresenceSyncer.Instance(self.identifier)
				room_syncer = RoomSyncer.Instance(self.identifier)
				
				affiliation_syncer.sync()
				presence_syncer.sync()
				room_syncer.sync()
			elif body == "debugtree":
				# EVENT: (Dev) print debug tree
				# TODO: Implement this! Not very urgent anymore, since UserCache/RoomCache have been removed.
				#builder = DebugTreeBuilder.Instance(self.identifier)
				#message_sender.send(recipient=sender, body=builder.build())
			
@LocalSingleton
class EvalHandler(LocalSingletonBase):
	def process(self, stanza):
		# EVENT: (Dev) eval command
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

@LocalSingleton
class OverrideHandler(LocalSingletonBase):
	def is_joined(self, jid, node, ifrom, data):
		# Override for the _is_joined_room method.
		# Checks whether a JID was already present in a room.
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		try:
			presence = presence_provider.find_by_session(jid, node)
			return True
		except NotFoundException, e:
			return False
	
	def get_joined(self, jid, node, ifrom, data):
		# Override for the _get_joined_rooms method.
		# Retrieves a list of all rooms a JID is present in.
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		try:
			return [presence.room.jid for presence in presence_provider.find_by_session(jid)]
		except NotFoundException, e:
			return []
		
	def add_joined(self, jid, node, ifrom, data):
		# Override for the _add_joined_room method.
		# Registers a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		user_provider.get(jid).register_join(node)
		
	def delete_joined(self, jid, node, ifrom, data):
		# Override for the _del_joined_room method.
		# Removes a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		user_provider.get(jid).register_leave(node)

from .notification import HighlightChecker
from .providers import UserProvider, PresenceProvider, AffiliationProvider, ConfigurationProvider
from .loggers import EventLogger, ApplicationLogger
from .component import Component
from .senders import MessageSender
from .db import Database, Row
from .sync import RoomSyncer, AffiliationSyncer, PresenceSyncer

from .util import Singleton, LocalSingleton, LocalSingletonBase

from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.xmlstream.matcher import MatchXPath, StanzaPath
from sleekxmpp.exceptions import IqError

import traceback, re

@LocalSingleton
class StanzaHandler(LocalSingletonBase):	
	def process(self, stanza):
		logger = ApplicationLogger.Instance(self.identifier)
		
		stanza = stanza['forwarded']['stanza']
		
		if isinstance(stanza, Iq):
			IqHandler.Instance(self.identifier).process(stanza)
		elif isinstance(stanza, Message):
			MessageHandler.Instance(self.identifier).process(stanza)
		elif isinstance(stanza, Presence):
			PresenceHandler.Instance(self.identifier).process(stanza)
		else:
			logger.warn("Unknown stanza type encountered: %s" % repr(stanza))

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
		EventLogger.Instance(self.identifier).log_message(user, room, "message", body, stanza) # TODO: Move parsing logic to event logger?
		
	def private_message(self, stanza):
		# EVENT: Private message received
		component = Component.Instance(self.identifier)
		dev_handler = DevelopmentCommandHandler.Instance(self.identifier)
		
		sender = stanza["from"].bare
		recipient = stanza["to"].bare
		body = stanza["body"]
		
		EventLogger.Instance(self.identifier).log_message(sender, recipient, "pm", body, stanza)
		
		if recipient == component.boundjid:
			dev_handler.process(stanza)
	
	def topic_change(self, stanza):
		# EVENT: Topic changed
		room = stanza['to'].bare
		user = stanza["from"].bare
		topic = stanza["subject"]
		
		EventLogger.Instance(self.identifier).log_event(user, room, "topic", topic, stanza)
	
@LocalSingleton	
class IqHandler(LocalSingletonBase):
	def process(self, stanza):
		logger = EventLogger.Instance(self.identifier)
		
		# In case it's necessary, the XPath for a ping is {jabber:client}iq/{urn:xmpp:ping}ping
		if MatchXPath("{jabber:client}iq/{urn:ietf:params:xml:ns:xmpp-session}session").match(stanza):
			# EVENT: User logged in
			user = stanza["from"]
			
			logger.log_event(user, None, "presence", "login", stanza)
		
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
			
			if recipient == "" or recipient == component.boundjid: # Ignore propagated presences
				user_provider.get(sender).set_status(type_)
				 
				if type_ == "available" or type_ in Presence.showtypes:
					# EVENT: User status changed
					logger.log_event(sender, "", "status", type_, stanza, message)
				elif type_ == "unavailable":
					# EVENT: User logged out
					logger.log_event(sender, "", "presence", "disconnect", stanza, message)
				
@LocalSingleton
class MucHandler(LocalSingletonBase):
	def process_join(self, stanza):
		# EVENT: User joined room
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		resource = stanza["to"].resource
		room = stanza["from"].bare
		nickname = stanza["from"].resource
		role = stanza["muc"]["role"]
		
		presence_provider.register_join(user, room, resource, nickname, role) # TODO: This might be better in a separate handler
		
	def process_leave(self, stanza):
		# EVENT: User left room
		presence_provider = PresenceProvider.Instance()
		
		user = stanza["to"]
		resource = stanza["to"].resource
		room = stanza["from"].bare
		
		presence_provider.register_leave(user, room, resource) # TODO: This might be better in a separate handler
		
	def process_presence(self, stanza):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		presence_provider = PresenceProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		room = stanza["from"].bare
		affiliation = stanza["muc"]["affiliation"]
		role = stanza["muc"]["role"]
		
		try:
			user = stanza["muc"]["jid"]
		except KeyError, e:
			return # No JID present
				
		if user != component.boundjid:
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
			body = stanza["body"].strip()
			
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
				pass
				#builder = DebugTreeBuilder.Instance(self.identifier)
				#message_sender.send(recipient=sender, body=builder.build())
			
@LocalSingleton
class EvalHandler(LocalSingletonBase):
	def process(self, stanza):
		# EVENT: (Dev) eval command
		message_sender = MessageSender.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
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
			logger.error("IqError: %s" % e.iq)
		except:
			message_sender.send(recipient=sender, body=unicode("Uncaught exception encountered:\n%s" % traceback.format_exc()))

@LocalSingleton
class OverrideHandler(LocalSingletonBase):
	def is_joined(self, jid, node, ifrom, data):
		# Override for the _is_joined_room method.
		# Checks whether a JID was already present in a room.
		presence_provider = PresenceProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		if jid != component.boundjid:
			try:
				presence = presence_provider.find_by_session(jid, node)
				return True
			except NotFoundException, e:
				return False
		else:
			return True
	
	def get_joined(self, jid, node, ifrom, data):
		# Override for the _get_joined_rooms method.
		# Retrieves a list of all rooms a JID is present in.
		presence_provider = PresenceProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		if jid != component.boundjid:
			try:
				return [presence.room.jid for presence in presence_provider.find_by_session(jid)]
			except NotFoundException, e:
				return []
		else:
			return [] # FIXME: Might need to return all rooms?
		
	def add_joined(self, jid, node, ifrom, data):
		# Override for the _add_joined_room method.
		# Registers a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		if jid != component.boundjid:
			user_provider.get(jid).register_join(node)
		
	def delete_joined(self, jid, node, ifrom, data):
		# Override for the _del_joined_room method.
		# Removes a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		if jid != component.boundjid:
			user_provider.get(jid).register_leave(node)

@LocalSingleton
class LogRequestHandler(LocalSingletonBase):
	def process(self, stanza):
		logger = ApplicationLogger.Instance(self.identifier)
		logger.warning(stanza)
		logger.warning(repr(stanza["mam"]["extended_support"]))
		
@LocalSingleton
class ResolveHandler(LocalSingletonBase):
	def resolve(self, message, stanza):
		queue = ResolverQueue.Instance(self.identifier)
		
		# IDEA: Perhaps have a qualifying string for each category of regexes; don't try to match regex until
		# qualifying string is present as a substring in the message. This should help performance.
		# TODO: Include tests.
		# FIXME: .Instance()s spawned here, might not be thread-safe!
		resolver_map = {
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_user, # May also indicate an organization, rather than a user
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_repository,
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/tree\/(?P<branch>[^\/?\s!]+)\/(?P<path>[^?]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_tree,
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/blob\/(?P<branch>[^\/?\s!]+)\/(?P<path>[^?]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_blob, # 'branch' can also point to a commit reference!
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/issues\/(?P<id>[0-9]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_issue,
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/pull\/(?P<id>[0-9]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_pullrequest,
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/commit\/(?P<id>[0-9a-f]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_commit,
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/compare\/(?P<id1>[0-9a-f]+)\.\.\.(?P<id2>[0-9a-f]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_comparison,
			"https?:\/\/gist\.github.com\/(?P<user>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_gist_user,
			"https?:\/\/gist\.github.com\/(?P<user>[^\/?\s!]+)\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_gist,
			"https?:\/\/imgur.com\/gallery\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": ImgurResolver.Instance(self.identifier).resolve_gallery_item,
			"https?:\/\/imgur.com\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": ImgurResolver.Instance(self.identifier).resolve_item, # This will trigger a false positive for URLs like imgur.com/random!
			"(?:\s|^|\()(?P<url>https?:\/\/.+\.(?P<type>svg|png|gif|bmp|jpg))": ImageResolver.Instance(self.identifier).resolve_item, # This is for generic image resolving (including i.imgur.com, since those URLs just carry image extensions)
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/\/?(?:\?.*)?": BeanstalkResolver.Instance(self.identifier).resolve_organization,
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/?(?:\?.*)?": BeanstalkResolver.Instance(self.identifier).resolve_repository,
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/changesets\/(?P<id>[0-9a-f]+)\/?(?:\?.*)?": BeanstalkResolver.Instance(self.identifier).resolve_changeset,
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/browse\/(?P<type>[^\/?\s!]+)(?:\/(?P<path>[^?]+))?\/?(?:\?(?:.+&)?ref=(?P<ref>[^\/&]+))?": BeanstalkResolver.Instance(self.identifier).resolve_path, # 'type' may refer to SVN subdir (trunk/tags/etc.) or 'git' for Git
			"https?:\/\/trello.com\/b\/(?P<id>[^\/?\s!]+)(?:\/(?P<name>[^\/?\s!]+))?\/?(?:\?.*)?": TrelloResolver.Instance(self.identifier).resolve_board,
			"https?:\/\/trello.com\/c\/(?P<id>[^\/?\s!]+)(?:\/(?P<name>[^\/?\s!]+))?\/?(?:\?.*)?": TrelloResolver.Instance(self.identifier).resolve_card,
			"https?:\/\/trello.com\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": TrelloResolver.Instance(self.identifier).resolve_user, # This may bring up false positives, eg. for trello.com/gold. It may also correspond to an organization rather than a user.
		}
		
		total_matches = 0
		
		for regex, resolver in resolver_map.iteritems():
			# IDEA: Store compiled regexes separately rather than rebuilding them every time, to improve performance.
			result = re.search("%s(?:\s|!|$)" % regex, message, re.IGNORECASE)
			
			if result is not None:
				# (resolver, matches, message, stanza)
				queue.add((resolver, result.groupdict(), message, stanza))
				total_matches += 1
				
		return total_matches

from .notification import HighlightChecker
from .providers import UserProvider, PresenceProvider, AffiliationProvider, ConfigurationProvider
from .loggers import EventLogger, ApplicationLogger
from .component import Component
from .senders import MessageSender
from .db import Database, Row
from .sync import RoomSyncer, AffiliationSyncer, PresenceSyncer, StatusSyncer
from .exceptions import NotFoundException
from .queue import ResolverQueue
from .resolvers import *

from .util import Singleton, LocalSingleton, LocalSingletonBase

from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.xmlstream.matcher import MatchXPath, StanzaPath
from sleekxmpp.exceptions import IqError

import traceback, re, datetime, time

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
		presence_provider = PresenceProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		user = stanza["to"]
		resource = stanza["to"].resource
		room = stanza["from"].bare
		nickname = stanza["from"].resource
		role = stanza["muc"]["role"]
		
		if user != component.boundjid:
			presence_provider.register_join(user, room, resource, nickname, role) # TODO: This might be better in a separate handler
		
	def process_leave(self, stanza):
		# EVENT: User left room
		presence_provider = PresenceProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		user = stanza["to"]
		resource = stanza["to"].resource
		room = stanza["from"].bare
		
		# This appears already taken care of in the API overrides.
		#if user != component.boundjid:
		#	presence_provider.register_leave(user, room, resource) # TODO: This might be better in a separate handler
		
	def process_presence(self, stanza):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		presence_provider = PresenceProvider.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		room_provider = RoomProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		database = Database.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		room = stanza["from"].bare
		affiliation = stanza["muc"]["affiliation"]
		role = stanza["muc"]["role"]
		nickname = stanza["from"].resource
		
		try:
			user = stanza["muc"]["jid"]
		except KeyError, e:
			return # No JID present
				
		if user != component.boundjid:
			if str(user) != "":
				try:
					affiliation_object = affiliation_provider.find_by_room_user(room, user)
					
					if affiliation_object.affiliation != affiliation:
						# EVENT: Affiliation change
						affiliation_object.change(affiliation)
				except NotFoundException, e:
					# No affiliation currently registered.
					# TODO: Perhaps abstract this.
					row = Row()
					row["UserId"] = user_provider.normalize_user(user).id
					row["RoomId"] = room_provider.normalize_room(room).id
					row["Affiliation"] = affiliation_provider.affiliation_number(affiliation)
					database["affiliations"].append(row)
					affiliation = affiliation_provider.wrap(row)
				
				try:
					presence_object = presence_provider.find_by_session(user, room=room)
				except NotFoundException, e:
					logger.warning("We were not aware of a MUC presence, this is bad! Room is %s and user is %s. Registering as a join..." % (room, user))
					presence_object = presence_provider.register_join(user, room, user.resource, nickname, role)
				
				if presence_object.role != role:
					# EVENT: Role change
					presence_object.change_role(role)
			else:
				# FIXME: This fires for the component. Does it also do so for users?
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
			# Originally, it always returned True for this case; however, unexpectly
			# it turned out to break MUC join detection. Since SleekXMPP relies on
			# this function to determine presence in a room, it was convinced that
			# the join by the component was a fake or mistake; after all, this method
			# would state that it was already joined. SleekXMPP therefore ignored
			# the join event, never registered it, and thus caused a timeout. It now
			# keeps an internal cache of joined rooms instead. It does not have to be
			# stored in the database, because the runtime cache is consistent with
			# the component state; if the cache disappears because the component
			# quits, it also implicitly leaves all channels.
			return (node in component.joined_rooms)
	
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
			return component.joined_rooms
		
	def add_joined(self, jid, node, ifrom, data):
		# Override for the _add_joined_room method.
		# Registers a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		if jid != component.boundjid:
			user_provider.get(jid).register_join(node, jid.resource, data, "unknown")
		else:
			component.joined_rooms.append(node)
		
	def delete_joined(self, jid, node, ifrom, data):
		# Override for the _del_joined_room method.
		# Removes a JID presence in a room.
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		if jid != component.boundjid:
			user_provider.get(jid).register_leave(node, jid.resource)
		else:
			component.joined_rooms.remove(node)

@LocalSingleton
class LogRequestHandler(LocalSingletonBase):
	def process(self, stanza):
		component = Component.Instance(self.identifier)
		logentry_provider = LogEntryProvider.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		filter_user = stanza["mam"]["with"]
		filter_start = stanza["mam"]["start"]
		filter_end = stanza["mam"]["end"]
		
		rsm_after = stanza["mam"]["rsm"]["after"]
		rsm_before = stanza["mam"]["rsm"]["before"]
		rsm_max = stanza["mam"]["rsm"]["max"]
		
		requesting_user = stanza["from"].bare
		extended = stanza["mam"]["extended_support"]
		
		predicates = []
		values = []
		
		# We only return stanzas where the requesting user is either the sender or the recipient.
		predicates.append("(`Sender` = ? OR `Recipient` = ?)")
		values = values + [requesting_user, requesting_user]
		
		if filter_user != "":
			predicates.append("(`Sender` = ? OR `Recipient` = ?)")
			values = values + [filter_user, filter_user]
			
		if filter_start != "":
			predicates.append("`Date` >= ?")
			values.append(filter_start)
			
		if time.mktime(filter_end.timetuple()) > (60 * 60 * 24): # WTF? Why is it returning January 1, 1970 when the element does not exist?
			predicates.append("`Date` <= ?")
			values.append(filter_end)
			
		if rsm_after != "":
			predicates.append("`OrderId` > (SELECT `OrderId` FROM %(table)s WHERE `Id` = ? LIMIT 1)")
			values.append(rsm_after)
			
		if rsm_before != "" and rsm_before is not None and rsm_before != True: # Deals with implementation inconsistency in SleekXMPP
			predicates.append("`OrderId` < (SELECT `OrderId` FROM %(table)s WHERE `Id` = ? LIMIT 1)")
			values.append(rsm_before)
		
		base_query = "SELECT * FROM %(table)s WHERE " + " AND ".join(predicates)
		
		if rsm_before == True: # Special case, return last page...
			message_query = base_query % {"table": "log_messages"} + " ORDER BY `OrderId` DESC"
			message_query = "(%s) ORDER BY `OrderId` ASC" % message_query
		else:
			message_query = base_query % {"table": "log_messages"} + " ORDER BY `OrderId` ASC"
		
		if rsm_max != "":
			message_query += " LIMIT %d" % int(rsm_max)
		
		try:
			print "query"
			print message_query
			print values
			messages = logentry_provider.get_messages_from_query(message_query, values)
		except NotFoundException, e:
			messages = []
		
		if len(messages) > 0:
			if extended and len(messages) > 1: # Only fetch events if we have at least two messages
				# TODO: This is a sub-optimal implementation. It currently looks for the (paged) messages
				# matching the predicates first, then selects all events inbetween the first and the last
				# matched message. Why? Because events and messages are stored and counted
				# separately, and we can't use RSM to page through two collections at the same time.
				# This could probably be optimized/improved with some SQL magicks in the future.
				# Bonus drawback of current approach: No way to tell with any certainty what came
				# first when an event and a message both have the same timestamp.
				start_boundary = messages[0].date
				end_boundary = messages[-1].date
				# TODO: Could be optimized by leaving out earlier `Date` and RSM predicates if present.
				event_query = base_query % {"table": "log_events"} + " AND `Date` > ? AND `Date` < ? ORDER BY `OrderId` ASC"
				values += [start_boundary, end_boundary]
				
				try:
					events = logentry_provider.get_events_from_query(event_query, values)
				except NotFoundException, e:
					events = []
				
				combined = messages + events
				combined.sort(key=lambda item: item.date)
			else:
				combined = messages
				
			# Send the stanzas to the requesting entity
			for item in combined:
				item_stanza = stanza.stream._build_stanza(ET.fromstring(item.stanza))
				# Need to build this stanza manually; the forwarding module will send it straight-away, but
				# we want to wrap it in a <result /> first.
				msg = component.Message()
				msg["to"] = stanza["from"]
				msg["from"] = component.boundjid
				msg["body"] = None
				msg["mam_result"]["id"] = item.id
				msg["mam_result"]["forwarded"]["stanza"] = item_stanza
				msg["mam_result"]["forwarded"]["delay"]["stamp"] = item.date
				
				try:
					msg["mam_result"]["queryid"] = stanza["id"]
				except KeyError, e:
					pass # No ID specified
				    
				msg.send()
				
			# Finished
			stanza.reply().send()
		else:
			logger.warning("No results.")
			pass # No results
		
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
			"https?:\/\/github.com\/(?P<user>[^\/?\s!]+)\/(?P<repository>[^\/?\s!]+)\/compare\/(?P<id1>[0-9a-f]+)\.\.\.(?P<id2>[0-9a-f]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_comparison,# TODO: Allow comparisons between things other than SHA hashes?
			"https?:\/\/gist\.github.com\/(?P<user>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_gist_user,
			"https?:\/\/gist\.github.com\/(?P<user>[^\/?\s!]+)\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": GitHubResolver.Instance(self.identifier).resolve_gist,
			"https?:\/\/imgur.com\/gallery\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": ImgurResolver.Instance(self.identifier).resolve_gallery_item,
			"https?:\/\/imgur.com\/(?P<id>[^\/?\s!]+)\/?(?:\?.*)?": ImgurResolver.Instance(self.identifier).resolve_item, # This will trigger a false positive for URLs like imgur.com/random!
			"(?:\s|^|\()(?P<url>https?:\/\/.+\.(?P<type>svg|png|gif|bmp|jpg))": ImageResolver.Instance(self.identifier).resolve_item, # This is for generic image resolving (including i.imgur.com, since those URLs just carry image extensions)
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/?(?:\?.*)?": BeanstalkResolver.Instance(self.identifier).resolve_repository,
			"https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/changesets\/(?P<id>[0-9a-f]+)\/?(?:\?.*)?": BeanstalkResolver.Instance(self.identifier).resolve_changeset,
			# [there does not appear to currently be support for this in the API] "https?:\/\/(?P<organization>[^.]+)\.beanstalkapp\.com\/(?P<repository>[^\/?\s!]+)\/browse\/(?P<type>[^\/?\s!]+)(?:\/(?P<path>[^?]+))?\/?(?:\?(?:.+&)?ref=(?P<ref>[^\/&]+))?": BeanstalkResolver.Instance(self.identifier).resolve_path, # 'type' may refer to SVN subdir (trunk/tags/etc.) or 'git' for Git
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

@LocalSingleton
class ZeromqEventHandler(LocalSingletonBase):
	def process(self, message):
		logger = ApplicationLogger.Instance(self.identifier)
		
		if message["type"] == "update_fqdn":
			# FQDN settings have been updated, Prosody configuration needs to be regenerated.
			pass
		elif message["type"] == "create_room":
			# A new room was created, this needs to be announced to clients.
			# Not implemented yet, the client currently uses polling.
			logger.debug("create_room")
		elif message["type"] == "update_vcard":
			# The vCard data for a user was updated, and the vCard file needs to be regenerated.
			jid = message["args"]["jid"]

from .notification import HighlightChecker
from .providers import UserProvider, PresenceProvider, AffiliationProvider, ConfigurationProvider, LogEntryProvider, RoomProvider
from .loggers import EventLogger, ApplicationLogger
from .component import Component
from .senders import MessageSender
from .db import Database, Row
from .sync import RoomSyncer, AffiliationSyncer, PresenceSyncer, StatusSyncer
from .exceptions import NotFoundException
from .queue import ResolverQueue
from .resolvers import *

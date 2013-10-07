#!/usr/bin/env python

import sys, re, logging
from datetime import datetime

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.xmlstream.matcher import MatchXPath, StanzaPath
from sleekxmpp.jid import JID

from sleekxmpp.exceptions import IqError

from util import state
from util.dedup import dedup

reload(sys)
sys.setdefaultencoding('utf8')

class Component(ComponentXMPP):
	def __init__(self, jid, host, port, password, conference_host):
		ComponentXMPP.__init__(self, jid, password, host, port)
		
		self.conference_host = conference_host
		
		self.add_event_handler("forwarded_stanza", self._envoy_handle_stanza)
		self.add_event_handler("groupchat_joined", self._envoy_handle_group_join)
		self.add_event_handler("groupchat_left", self._envoy_handle_group_leave)
		self.add_event_handler("groupchat_presence", self._envoy_handle_group_presence)
		self.add_event_handler("session_start", self._envoy_start)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
		self._envoy_events = {}
		self._envoy_members = {}
		self._envoy_user_cache = UserCache()
		
		# We can't check all the presences straight away, because the component hasn't connected yet - it
		# will hang while waiting for an <iq /> response that never comes. We'll therefore do the first
		# check (and set the timer) in the session_start event, defined in the _envoy_start method.
	
	def _envoy_start(self, event):
		self.scheduler.add("Purge Presences", 300, self._envoy_purge_presences, repeat=True)
		self._envoy_purge_presences()
	
	def _envoy_update_roster(self, room):
		self._envoy_members[room] = []
		
		# TODO: Also add admins to this list
		try:
			for item in self['xep_0045'].get_users(room, ifrom=self.boundjid, affiliation="member")['muc_admin']['items']:
				if item['jid'] not in self._envoy_members[room]:
					self._envoy_members[room].append(item['jid'])
		except IqError, e:
			pass  # The room doesn't exist anymore
	
	def _envoy_purge_presences(self):
		logging.info("Purging outdated presences")
		
		current_presences = {}
		
		room_list = self['xep_0045'].get_rooms(ifrom=self.boundjid, jid=self.conference_host)['disco_items']['items']
		
		for room in room_list:
			# TODO: Keep a room cache?
			room_jid, room_node, room_name = room
			
			# We will do a two pass here. On the first pass, all missing rooms are added. On the second pass, all
			# outdated presences are removed. This way, there won't be any chance of race conditions, as there would
			# be when clearing the cache first and then re-filling it.
			presences = (self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, role="visitor")['muc_admin']['items'] +
			             self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, role="participant")['muc_admin']['items'] +
			             self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, role="moderator")['muc_admin']['items'])
			
			for user in presences:
				cache_user = self._envoy_user_cache.get(user['jid'].bare)
				
				if not cache_user.in_room(room_jid):
					cache_user.add_room(room_jid, user['jid'].resource)
				
			current_presences[room_jid] = [unicode(user['jid']) for user in presences]
		
		logging.debug("Current presences according to XMPP daemon: %s" % current_presences)
		
		for jid, user in self._envoy_user_cache.cache.items():
			logging.debug("Current UserCache room presence list for %s: %s" % (user.jid, user.rooms))
			for room, resources in user.rooms.items():
				for resource in resources:
					try:
						if "%s/%s" % (jid, resource) not in current_presences[room]:
							user.remove_room(room, resource)
					except KeyError, e:
						user.remove_room(room, resource)
			
			for room, resources in user.rooms.iteritems():
				user.rooms[room] = dedup(resources)
		
		logging.debug("New presence list: %s" % [(jid, user.rooms) for jid, user in self._envoy_user_cache.cache.iteritems()])
		
		# Finally, we'll also want to make sure that we have up to date affiliation information
		# for all the users.
		
		for room in room_list:
			room_jid, room_node, room_name = room
			
			affiliations = (self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, affiliation="owner")['muc_admin']['items'] +
			                self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, affiliation="admin")['muc_admin']['items'] +
			                self['xep_0045'].get_users(room_jid, ifrom=self.boundjid, affiliation="member")['muc_admin']['items'])
			
			for user in affiliations:
				cache_user = self._envoy_user_cache.get(user['jid'].bare)
				affiliation = user['affiliation']
				
				if cache_user.get_affiliation(room_jid) != affiliation:
					cache_user.set_affiliation(room_jid, affiliation)
					
		logging.debug("Affiliation list updated")
		
		self._envoy_call_event("presences_purged")
		
	def _envoy_handle_stanza(self, wrapper):
		stanza = wrapper['forwarded']['stanza']
		
		outfile = open("raw.log", "a+")
		outfile.write("%s - %s\n" % (datetime.now().isoformat(), stanza))
		outfile.close()
		
		if isinstance(stanza, Iq):
			self._envoy_handle_iq(wrapper, stanza)
		elif isinstance(stanza, Message):
			self._envoy_handle_message(wrapper, stanza)
		elif isinstance(stanza, Presence):
			self._envoy_handle_presence(wrapper, stanza)
		else:
			logging.warn("Unknown stanza type encountered: %s" % repr(stanza))
	
	def _envoy_handle_iq(self, wrapper, stanza):
		if MatchXPath("{jabber:client}iq/{urn:xmpp:ping}ping").match(stanza):
			self._envoy_call_event("ping", stanza["from"])
		elif MatchXPath("{jabber:client}iq/{urn:ietf:params:xml:ns:xmpp-session}session").match(stanza):
			self._envoy_call_event("login", stanza["from"])
		return
		
	def _envoy_handle_message(self, wrapper, stanza):
		if stanza.match('message@type=groupchat/body'):
			room = stanza['to'].bare
			self._envoy_user_cache.touch(stanza["from"].bare)
			self._envoy_call_event("group_message", stanza["from"], room, stanza["body"])
			
			if stanza['to'].bare not in self._envoy_members:
				# The message was addressed at someone that, according to our internal bookkeeping, isn't in the room.
				# Update the bookkeeping to correct this, by asking the xmppd.
				self._envoy_update_roster(room)
			
			highlights = re.findall("@([a-zA-Z0-9._-]+)", stanza["body"])
			for highlight in highlights:
				if highlight == "all":
					# Highlight everyone in the room
					affected_users = set(self._envoy_user_cache.find_by_room_presence(room) +
					                  self._envoy_user_cache.find_by_room_membership(room))
					for user in affected_users:
						if str(user.jid) != str(stanza["from"].bare):
							self._envoy_call_event("group_highlight", stanza["from"], JID(user.jid), JID(room), stanza["body"], highlight)
				else:
					# Highlight one particular nickname
					for user in self._envoy_user_cache.find_nickname(highlight):
						if user.in_room(room):
							self._envoy_call_event("group_highlight", stanza["from"], JID(user.jid), JID(room), stanza["body"], highlight)
							#logging.error("Highlighted user %s in room %s!" % (user.jid, room))
				#self._envoy_call_event("groupchat_highlight")
				#if highlight in [jid.username for jid in self._envoy_members[stanza['to'].bare]]:
				#	print "### User %s was highlighted in %s!" % (highlight, stanza['to'].bare)
		elif stanza.match('message@type=groupchat/subject'):
			self._envoy_user_cache.touch(stanza["from"].bare)
			self._envoy_call_event("topic_change", stanza["from"], stanza["to"], stanza["subject"])
		elif stanza.match('message@type=chat/body'):
			self._envoy_user_cache.touch(stanza["from"].bare)
			self._envoy_user_cache.touch(stanza["to"].bare)
			self._envoy_call_event("private_message", stanza["from"], stanza["to"], stanza["body"])
		
	def _envoy_handle_presence(self, wrapper, stanza):
		stanza_type = stanza["type"]
		
		if stanza.match('presence/muc'):
			self['xep_0045']._handle_presence(stanza)
			#print self['xep_0045'].get_rooms(ifrom=self.boundjid, jid="conference.envoy.local")
		else:
			# User presence
			# We really only want to process status changes if they're the original message.
			# We don't really care about the rebroadcasts to various places.
			if stanza["to"] == "":
				self._envoy_user_cache.get(stanza["from"].bare).update_presence(state.from_string(stanza["type"]))
				
				if stanza_type == "available" or stanza_type in Presence.showtypes:
					self._envoy_call_event("status", stanza["from"], stanza["type"], stanza["status"])
				elif stanza_type == "unavailable":
					self._envoy_call_event("logout", stanza["from"], stanza["status"])
				
	def _envoy_handle_group_join(self, stanza):
		user = stanza["to"]
		room = stanza["from"].bare
		nickname = stanza["from"].resource
		
		# Update presence in the user cache
		self._envoy_user_cache.get(user.bare).add_room(room, user.resource)
		
		# Update affiliation in the user cache
		affiliation = stanza['muc']['affiliation']
		self._envoy_user_cache.get(user.bare).set_affiliation(room, affiliation)
		
		# Handle event
		self._envoy_call_event("join", user, JID(room), nickname)
		
		# We can optimize this by updating the roster once and tracking state changes from then on
		self._envoy_update_roster(room)
			
	def _envoy_handle_group_leave(self, stanza):
		user = stanza["to"]
		room = stanza["from"].bare
		self._envoy_user_cache.get(user.bare).remove_room(room, user.resource)
		self._envoy_call_event("leave", user, JID(room))
		# We can optimize this by updating the roster once and tracking state changes from then on
		self._envoy_update_roster(room)
	
	def _envoy_handle_group_presence(self, stanza):
		# FIXME: It's possible that an affiliation is not updated, if the target user is in a semi-anonymous
		#        room, and no moderators are present. In that case, whether a stanza containing the full JID
		#        of the affected user is sent out, depends on the implementation of the XMPP daemon. The
		#        XEP-0045 specification does not explicitly indicate what the daemon should do in this case.
		#        Prosody is known to send the JID along with the presence stanza that is targeted at the
		#        affected user, _even_ if said user is not a moderator. According to developers, this is not
		#        expected to change in later Prosody versions, therefore as long as Prosody is used, it
		#        should be possible to rely on this behaviour.
		room = stanza["from"].bare
		user = stanza["muc"]["jid"]
		affiliation = stanza["muc"]["affiliation"]
		
		if user != "":
			# TODO: Implement event for changing affiliation?
			self._envoy_user_cache.get(user.bare).set_affiliation(room, affiliation)
	
	def _envoy_call_event(self, event_name, *args, **kwargs):
		try:
			self._envoy_events[event_name](*args, **kwargs)
		except KeyError, e:
			# No function has been registered for this event
			pass
		
	def register_event(self, event_name, func):
		self._envoy_events[event_name] = func

class NodeCache(object):
	def __init__(self):
		self.cache = {}
		
	def touch(self, jid):
		if jid not in self.cache:
			logging.debug("Created %s item %s" % (self.__class__, jid))
			self.cache[jid] = self.item_factory(jid)
		
	def get(self, jid):
		try:
			return self.cache[jid]
		except KeyError, e:
			self.touch(jid)
			return self.cache[jid]

class NodeCacheItem(object):
	def __init__(self, jid):
		self.jid = jid
	
	def __eq__(self, other):
		return (str(self.jid) == str(other.jid))
		
	def __hash__(self):
		return hash(("jid", str(self.jid)))

class UserCache(NodeCache):
	def __init__(self, *args, **kwargs):
		NodeCache.__init__(self, *args, **kwargs)
		self.item_factory = UserCacheItem
			
	def find_nickname(self, nickname):
		return [user for jid, user in self.cache.iteritems() if user.nickname == nickname][:1]
	
	def find_by_room_presence(self, room):
		return [user for jid, user in self.cache.iteritems() if room in user.rooms]
	
	def find_by_room_membership(self, room):
		return [user for jid, user in self.cache.iteritems() if room in user.affiliations and user.affiliations[room] != "none" and user.affiliations[room] != "outcast"]
	
	def get_debug_tree(self):
		output = "Debug tree\n"
		
		for jid, user in self.cache.iteritems():
			output += "\t" + "- %s\n" % user.jid
			
			output += "\t\t" + "- Room presences\n"
			for room in user.rooms:
				output += "\t\t\t" + "* %s\n" % room
			
			output += "\t\t" + "- Affiliations\n"
			for room, affiliation in user.affiliations.iteritems():
				output += "\t\t\t" + "* %s: %s\n" % (room, affiliation)
				
			properties = {
				"First Name": user.first_name,
				"Last Name": user.last_name,
				"Full Name": user.full_name,
				"Job Title": user.job_title,
				"E-mail Address": user.email_address,
				"Nickname": user.nickname,
				"Mobile Number": user.mobile_number,
				"Status": state.from_state(user.presence)
			}
			
			for key, val in properties.iteritems():
				output += "\t\t" + "- %s\n" % key
				output += "\t\t\t" + "%s\n" % val
			
			output += "\n"
			
		return output
			
class UserCacheItem(NodeCacheItem):
	def __init__(self, jid):
		NodeCacheItem.__init__(self, jid)
		self.presence = state.UNKNOWN
		self.rooms = {}
		self.affiliations = {}
		self.first_name = ""
		self.last_name = ""
		self.full_name = ""
		self.job_title = ""
		self.email_address = ""
		self.nickname = ""
		self.mobile_number = ""
	
	def update_presence(self, presence):
		logging.debug("Changing presence for user %s to %s" % (self.jid, state.from_state(presence)))
		self.presence = presence
		
	def add_room(self, room, resource):
		logging.debug("Adding presence from user %s/%s for room %s" % (self.jid, resource, room))
		
		try:
			self.rooms[room].append(resource)
		except KeyError, e:
			self.rooms[room] = [resource]
			
	def remove_room(self, room, resource):
		logging.debug("Removing presence from user %s/%s for room %s" % (self.jid, resource, room))
		
		try:
			self.rooms[room] = [x for x in self.rooms[room] if x != resource]
			
			if len(self.rooms[room]) == 0:
				del self.rooms[room]
		except KeyError, e:
			logging.warning("Tried to remove presence for %s/%s from %s, but this presence was not previously known" % (self.jid, resource, room))
		
	def in_room(self, room):
		return (room in self.rooms)
		
	def set_affiliation(self, room, affiliation):
		logging.debug("Changing affiliation for user %s in room %s to %s" % (self.jid, room, affiliation))
		self.affiliations[room] = affiliation
		
	def get_affiliation(self, room):
		try:
			return self.affiliations[room]
		except KeyError, e:
			return "none"
			
	def is_affiliated_to(self, room):
		return (self.get_affiliation(room) not in ("none", "outcast"))
		
	def is_guest_in(self, room):
		return (self.get_affiliation(room) == "none")
		
	def is_banned_from(self, room):
		return (self.get_affiliation(room) == "outcast")
		
	def update_vcard(self, data):
		# first_name, last_name, job_title, email_address, nickname
		update_name = False
		
		if "first_name" in data:
			self.first_name = data["first_name"]
			update_name = True
			
		if "last_name" in data:
			self.last_name = data["last_name"]
			update_name = True
			
		if update_name:
			self.full_name = "%s %s" % (self.first_name, self.last_name)
			
		if "job_title" in data:
			self.job_title = data["job_title"]
		
		if "email_address" in data:
			self.email_address = data["email_address"]
			
		if "nickname" in data:
			self.nickname = data["nickname"]
			
		if "mobile_number" in data:
			self.mobile_number = data["mobile_number"]

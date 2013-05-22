#!/usr/bin/env python

import sys
from datetime import datetime

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.xmlstream.matcher import MatchXPath, StanzaPath

reload(sys)
sys.setdefaultencoding('utf8')

class Component(ComponentXMPP):
	def __init__(self, jid, host, port, password):
		ComponentXMPP.__init__(self, jid, password, host, port)
		self.add_event_handler("forwarded_stanza", self._envoy_handle_stanza)
		self.add_event_handler("groupchat_joined", self._envoy_handle_group_join)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
		self._envoy_events = {}
		
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
			print "Unknown:", repr(stanza) # TODO: Log unknown stanza type
	
	def _envoy_handle_iq(self, wrapper, stanza):
		if MatchXPath("{jabber:client}iq/{urn:xmpp:ping}ping").match(stanza):
			self._envoy_call_event("ping", stanza["from"])
		elif MatchXPath("{jabber:client}iq/{urn:ietf:params:xml:ns:xmpp-session}session").match(stanza):
			self._envoy_call_event("login", stanza["from"])
		return
		
	def _envoy_handle_message(self, wrapper, stanza):
		if stanza.match('message@type=groupchat/body'):
			self._envoy_call_event("group_message", stanza["from"], stanza["to"], stanza["body"])
		elif stanza.match('message@type=groupchat/subject'):
			self._envoy_call_event("topic_change", stanza["from"], stanza["to"], stanza["subject"])
		elif stanza.match('message@type=chat/body'):
			self._envoy_call_event("private_message", stanza["from"], stanza["to"], stanza["body"])
		
	def _envoy_handle_presence(self, wrapper, stanza):
		# TODO: XMPP mandates that the status code 110 is always returned when the presence is 'available'.
		#       It's not possible to dettermine whether the presence is a MUC join or a status change. We'll
		#       need to keep track of this internally, to avoid erroneous logs.
		if stanza.match('presence/muc'):
			self['xep_0045']._handle_presence(stanza)
		else:
			# User presence
			stanza_type = stanza["type"]
			
			# We really only want to process status changes if they're the original message.
			# We don't really care about the rebroadcasts to various places.
			if stanza["to"] == "":
				if stanza_type == "available" or stanza_type in Presence.showtypes:
					self._envoy_call_event("status", stanza["from"], stanza["type"], stanza["status"])
				elif stanza_type == "unavailable":
					self._envoy_call_event("logout", stanza["from"], stanza["status"])
				
	def _envoy_handle_group_join(self, stanza):
		self._envoy_call_event("join", stanza["to"], stanza["from"].bare)
		
	def _envoy_call_event(self, event_name, *args, **kwargs):
		try:
			self._envoy_events[event_name](*args, **kwargs)
		except KeyError, e:
			# No function has been registered for this event
			pass
		
	def register_event(self, event_name, func):
		self._envoy_events[event_name] = func

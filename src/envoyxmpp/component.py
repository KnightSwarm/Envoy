#!/usr/bin/env python

import sys

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
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
		self._envoy_events = {}
		
	def _envoy_handle_stanza(self, wrapper):
		stanza = wrapper['forwarded']['stanza']
		#print stanza
		
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
		print "Msg:", stanza
		
	def _envoy_handle_presence(self, wrapper, stanza):
		if StanzaPath("presence@type=unavailable").match(stanza):
			self._envoy_call_event("logout", stanza["from"], stanza["status"])
		elif MatchXPath("{jabber:client}presence/{jabber:client}show").match(stanza):
			self._envoy_call_event("status", stanza["from"], stanza["show"], stanza["status"])
		else:
			# Most likely the user switched to 'available'
			self._envoy_call_event("status", stanza["from"], "available", stanza["status"])
		return
		
	def _envoy_call_event(self, event_name, *args, **kwargs):
		try:
			self._envoy_events[event_name](*args, **kwargs)
		except KeyError, e:
			# No function has been registered for this event
			pass
		
	def register_event(self, event_name, func):
		self._envoy_events[event_name] = func

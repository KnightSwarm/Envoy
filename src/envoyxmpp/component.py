#!/usr/bin/env python

import sys

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP

reload(sys)
sys.setdefaultencoding('utf8')

class Component(ComponentXMPP):
	def __init__(self, jid, host, port, password):
		ComponentXMPP.__init__(self, jid, password, host, port)
		self.add_event_handler("forwarded_stanza", self._handle_stanza)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
	def _handle_stanza(self, stanza):
		print stanza

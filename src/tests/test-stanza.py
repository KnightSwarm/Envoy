#!/usr/bin/env python

import sys
import logging
from optparse import OptionParser

import sleekxmpp

reload(sys)
sys.setdefaultencoding('utf8')

class SendMsgBot(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password, stanza):
		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		self.stz = stanza
		self.add_event_handler("session_start", self.start)

	def start(self, event):
		self.send_presence()
		self.get_roster()
		self.send_raw(self.stz)
		self.disconnect(wait=True)


if __name__ == '__main__':
	username = "testuser@envoy.local"
	password = "testpass"
	stanza = sys.argv[1]

	xmpp = SendMsgBot(username, password, stanza)
	xmpp.register_plugin('xep_0030') # Service Discovery
	xmpp.register_plugin('xep_0199') # XMPP Ping

	if xmpp.connect():
		xmpp.process(block=True)
		print("Done")
	else:
		print("Unable to connect.")

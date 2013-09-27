# Local imports
import xmpp

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from PyQt4 import QtCore

from sleekxmpp.exceptions import IqError, IqTimeout

class ApplicationThread(QtCore.QThread):
	def run(self):
		global main_application
		main_application = Application()
		main_application.connect("testuser2@envoy.local", "testpass")
	
	def __del__(self):
		pass # Shutdown code goes here

class Application(object):
	# Main application code (SleekXMPP, etc.) goes here
	def __init__(self):
		pass
		
	def connect(self, jid, password):
		self.xmpp = xmpp.Client(jid, password)
		self.xmpp.connect()
		self.xmpp.process(block=False)
		
	def on_muc_message(self, message):
		print "MUC (from %s): %s" % (message['from'], message['body'])
		
	def on_private_message(self, message):
		print "Private (from %s): %s" % (message['from'], message['body'])

# Local imports
import xmpp, thread

import logging, time
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from PyQt4 import QtCore

from sleekxmpp.exceptions import IqError, IqTimeout

class ApplicationThread(thread.BaseThread):
	@QtCore.pyqtSlot()
	def run(self):
		global main_application
		main_application = Application()
		main_application.connect("testuser2@envoy.local", "testpass")
	
	@QtCore.pyqtSlot()
	def shutdown(self):
		logging.info("[application] Shutting down client...")
		main_application.xmpp.disconnect()
		logging.info("[application] Client disconnected, waiting for all threads to exit...")
	
	def done(self):
		# Shutdown code goes here
		pass
		# TODO: Not sure what to do with this method... it runs after cleanly finishing, but may not be very useful.

class Application(object):
	# Main application code (SleekXMPP, etc.) goes here
	def __init__(self):
		pass
		
	def connect(self, jid, password):
		self.xmpp = xmpp.Client(jid, password)
		self.xmpp.connect()
		self.xmpp.process(block=True)
		
	def on_muc_message(self, message):
		print "MUC (from %s): %s" % (message['from'], message['body'])
		
	def on_private_message(self, message):
		print "Private (from %s): %s" % (message['from'], message['body'])

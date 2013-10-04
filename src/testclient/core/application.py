# Local imports
import xmpp, thread

import logging, time
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from PyQt4 import QtCore

from sleekxmpp.exceptions import IqError, IqTimeout

class Room(object):
	def __init__(self, room_name):
		self.name = room_name

class ApplicationThread(thread.BaseThread):
	def __init__(self, *args, **kwargs):
		thread.BaseThread.__init__(self, *args, **kwargs)
		self.main_application = Application()
		
	@QtCore.pyqtSlot()
	def run(self):
		self.main_application.connect("testuser2@envoy.local", "testpass")
	
	@QtCore.pyqtSlot()
	def shutdown(self):
		logging.info("[application] Shutting down client...")
		self.main_application.xmpp.disconnect()
		logging.info("[application] Client disconnected, waiting for all threads to exit...")
	
	def done(self):
		# Shutdown code goes here
		pass
		# TODO: Not sure what to do with this method... it runs after cleanly finishing, but may not be very useful.

class Application(QtCore.QObject):
	# Main application code (SleekXMPP, etc.) goes here
	# This lives in the application thread
	event_signal = QtCore.pyqtSignal(str, dict)
	
	def __init__(self):
		QtCore.QObject.__init__(self)
		self.handler = ApplicationHandler(self)
		self.event_signal.connect(self.handler.receive_event)
		
	def connect(self, jid, password):
		self.xmpp = xmpp.Client(jid, password)
		self.xmpp.connect()
		self.xmpp.process(block=True)
		
	def on_muc_message(self, message):
		print "MUC (from %s): %s" % (message['from'], message['body'])
		
	def on_private_message(self, message):
		print "Private (from %s): %s" % (message['from'], message['body'])
	
	def fire_event(self, event, data):
		
		pass#
		
	@QtCore.pyqtSlot(str, dict)
	def receive_event(self, event, data):
		pass#

class ApplicationHandler(QtCore.QObject):
	# This lives in the GUI thread
	event_signal = QtCore.pyqtSignal(str, dict)
	
	def __init__(self, application):
		QtCore.QObject.__init__(self)
		self.app = application
		
		self.event_signal.connect(self.app.receive_event)
		
		self._rooms = []
		
	def fire_event(self, event, data):
		pass#
	
	@QtCore.pyqtSlot(str, dict)
	def receive_event(self, event, data):
		pass#

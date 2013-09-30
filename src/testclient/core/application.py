# Local imports
import xmpp

import logging, time
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from PyQt4 import QtCore

from sleekxmpp.exceptions import IqError, IqTimeout

class BaseThread(QtCore.QObject):
	# This acts as a wrapper for a QObject and a QThread
	shutdown_signal = QtCore.pyqtSignal()
	
	def __init__(self, *args, **kwargs):
		QtCore.QObject.__init__(self, *args, **kwargs)
		self.internal_thread = QtCore.QThread()
		self.worker = BaseThreadWorker()
		self.worker.run = self.run  # Copy run method to internal worker object
		self.worker.shutdown = self.shutdown  # Copy run method to internal worker object
	
	def __getattr__(self, name):
		# If the BaseThread object itself doesn't have a certain attribute,
		# we'll try to return it for the encapsulated worker object. This
		# way, signals for the worker can be accessed directly through the
		# Thread object.
		return getattr(self.worker, name)
	
	def start(self):
		self.worker.moveToThread(self.internal_thread)
		
		self.shutdown_signal.connect(self.worker.shutdown)
		self.worker.finished.connect(self.internal_thread.quit) #?
		self.internal_thread.started.connect(self.worker.start)
		self.internal_thread.finished.connect(self.done)
		print self.internal_thread.terminated
		self.internal_thread.start()
		
	def stop(self):
		self.shutdown_signal.emit()
		
	def done(self):
		pass
		
class BaseThreadWorker(QtCore.QObject):
	finished = QtCore.pyqtSignal()
	
	def start(self, *args, **kwargs):
		self.run(*args, **kwargs)
		self.finished.emit()
	
	@QtCore.pyqtSlot()
	def shutdown(self, *args, **kwargs):
		print "ABORT"
			
	def run(self):
		# Must override
		raise Exception("You must override the run() method.")

class ApplicationThread(BaseThread):
	@QtCore.pyqtSlot()
	def run(self):
		global main_application
		main_application = Application()
		main_application.connect("testuser2@envoy.local", "testpass")
		#for x in xrange(0, 5):
		#	print "hai"
		#	time.sleep(1)
	
	@QtCore.pyqtSlot()
	def shutdown(self):
		logging.info("[application] Shutting down client...")
		main_application.xmpp.disconnect()
		logging.info("[application] Client disconnected, waiting for all threads to exit...")
	
	def done(self):
		# Shutdown code goes here
		pass#print "SHUTDOWN"
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

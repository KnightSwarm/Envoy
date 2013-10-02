from PyQt4 import QtCore

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
		pass # May override for thread shutdown actions
			
	def run(self):
		# Must override
		raise Exception("You must override the run() method.")

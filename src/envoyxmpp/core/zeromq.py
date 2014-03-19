from .util import Singleton, LocalSingleton

import threading, json, zmq

@LocalSingleton
class ZeromqEventThread(threading.Thread):
	def __init__(self, singleton_identifier=None, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.identifier = singleton_identifier
		
	def run(self):
		logger = ApplicationLogger.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		logger.debug("Opening ZeroMQ event socket...")
		
		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PULL)
		self.socket.bind("tcp://127.0.0.1:18081")
		
		logger.info("ZeroMQ event socket opened.")
		
		while True:
			blob = self.socket.recv()
			
			logger.debug("Message received on ZeroMQ event socket: %s" % blob)
			
			try:
				message = json.loads(blob)
			except Exception, e:
				logger.warning("Received malformed message on ZeroMQ event socket; discarding. Exception raised was %s" % repr(e))
				continue # Discard.
				
			component.event("zmq_event", message)
				
from .loggers import ApplicationLogger
from .component import Component

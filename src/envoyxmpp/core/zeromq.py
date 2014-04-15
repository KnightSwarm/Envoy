from .util import Singleton, LocalSingleton

import threading, json, zmq

@LocalSingleton
class ZeromqEventThread(threading.Thread):
	def __init__(self, singleton_identifier=None, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.identifier = singleton_identifier
		self.stopped = False
		self.stop = False
		
	def run(self):
		logger = ApplicationLogger.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		logger.debug("Opening ZeroMQ event socket...")
		
		self.context = zmq.Context()
		
		self.poller = zmq.Poller()
		self.socket = self.context.socket(zmq.PULL)
		self.socket.bind("tcp://127.0.0.1:18081")
		self.poller.register(self.socket)
		
		logger.info("ZeroMQ event socket opened.")
		
		while self.stop == False:
			events = self.poller.poll(1000)
			
			if len(events) > 0:
				blob = self.socket.recv()
				
				logger.debug("Message received on ZeroMQ event socket: %s" % blob)
				
				try:
					message = json.loads(blob)
				except Exception, e:
					logger.warning("Received malformed message on ZeroMQ event socket; discarding. Exception raised was %s" % repr(e))
					continue # Discard.
					
				component.event("zmq_event", message)
				
		logger.debug("ZeroMQ event thread shutting down...")
		self.socket.close()
		self.stopped = True
				
from .loggers import ApplicationLogger
from .component import Component

from .util import Singleton, LocalSingleton, LocalSingletonBase

from Queue import Queue
from threading import Thread

@LocalSingleton
class ResolverQueue(Thread):
	# This is effectively just a thread. It lets resolves be queued, and then
	# uses a standard SleekXMPP event to queue the response. That event
	# is then further handled by the ResolveHandler. The responses are
	# routed through a SleekXMPP event, to ensure that they are handled
	# on the correct thread.
	def __init__(self, singleton_identifier=None):
		Thread.__init__(self)
		self.identifier = singleton_identifier
		self.q = Queue()
	
	def run(self):
		component = Component.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		logger.info("ResolverQueue thread started.")
		
		while True:
			resolver, match, message, stanza = self.q.get()
			result = resolver(match, message, stanza)
			component.event("resolve_finished", (result, stanza))
	
	def add(self, item):
		self.q.put(item)

from .component import Component
from .loggers import ApplicationLogger

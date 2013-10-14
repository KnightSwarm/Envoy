from sleekxmpp.util import Queue, QueueEmpty

class PyQueue(object):
	def __init__(self):
		self.internal_queue = Queue()
		
	def set_callback(self, callback):
		self.callback = callback
		
	def put(self, *args, **kwargs):
		self.internal_queue.put(*args, **kwargs)
		
	def check(self):
		try:
			item = self.internal_queue.get(block=False)
		except QueueEmpty:
			return
			
		self.callback(item)

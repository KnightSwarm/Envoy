from .util import Singleton, LocalSingleton, LocalSingletonBase

@LocalSingleton
class ResolverQueue(LocalSingletonBase):
	# Mock. Should queue eventually.
	
	def add(self, item):
		resolver, match, message, stanza = item
		
		result = resolver(match, message, stanza)
		print result

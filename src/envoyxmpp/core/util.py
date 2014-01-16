class Singleton:
	# http://stackoverflow.com/a/7346105/1332715
	"""
	A non-thread-safe helper class to ease implementing singletons.
	This should be used as a decorator -- not a metaclass -- to the
	class that should be a singleton.

	The decorated class can define one `__init__` function that
	takes only the `self` argument. Other than that, there are
	no restrictions that apply to the decorated class.

	To get the singleton instance, use the `Instance` method. Trying
	to use `__call__` will result in a `TypeError` being raised.

	Limitations: The decorated class cannot be inherited from.

	"""

	def __init__(self, decorated):
		self._decorated = decorated

	def Instance(self):
		"""
		Returns the singleton instance. Upon its first call, it creates a
		new instance of the decorated class and calls its `__init__` method.
		On all subsequent calls, the already created instance is returned.

		"""
		try:
			return self._instance
		except AttributeError:
			self._instance = self._decorated()
			return self._instance

	def __call__(self):
		raise TypeError('Singletons must be accessed through `Instance()`.')

	def __instancecheck__(self, inst):
		return isinstance(inst, self._decorated)

class LocalSingleton:
	# Derivative of above
	def __init__(self, decorated):
		self._decorated = decorated
		self._instance = {}

	def Instance(self, identifier):
		try:
			return self._instance[identifier]
		except KeyError:
			self._instance[identifier] = self._decorated(singleton_identifier=identifier)
			return self._instance[identifier]

	def __call__(self):
		raise TypeError('Singletons must be accessed through `Instance()`.')

	def __instancecheck__(self, inst):
		return isinstance(inst, self._decorated)

class LocalSingletonBase(object):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier

class LazyLoadingObject(object):
	def __getattr__(self, name):
		try:
			value = self.lazy_loaders[name](self)
		except AttributeError, e:
			raise AttributeError("Attribute not found, and no lazy loaders specified.")
		except KeyError, e:
			raise AttributeError("Attribute not found, and no lazy loaders found for the specified attribute.")
			
		setattr(self, name, value)
		return value

def dedup(seq):
	seen = set()
	seen_add = seen.add
	return [x for x in seq if x not in seen and not seen_add(x)]


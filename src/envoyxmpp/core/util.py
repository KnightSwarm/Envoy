try:
	import xml.etree.cElementTree as ET
except ImportError, e:
	import xml.etree.ElementTree as ET
	
import functools, re

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
			value = self.lazy_loaders[name]()
		except AttributeError, e:
			raise AttributeError("Attribute %s not found, and no lazy loaders specified." % name)
		except KeyError, e:
			raise AttributeError("Attribute %s not found, and no lazy loaders found for the specified attribute." % name)
			
		setattr(self, name, value)
		return value

def dedup(seq):
	seen = set()
	seen_add = seen.add
	return [x for x in seq if x not in seen and not seen_add(x)]

def cut_text(text, length):
	if len(text) > length:
		return "%s..." % re.match(r"^(.{0,%d})(\b|$)" % length, text).group(1)
	else:
		return text

# Source: http://effbot.org/zone/element-builder.htm
# (c) 2006 Fredrik Lundh
# Modifications (c) 2014 Sven Slootweg
class _E(object):
	def __call__(self, tag, *children, **attrib):
		attrib = {attribute.rstrip("_").replace("_", "-"): unicode(value) for attribute, value in attrib.iteritems()}
		elem = ET.Element(tag, attrib)
		for item in children:
			if isinstance(item, dict):
				elem.attrib.update(item)
			elif ET.iselement(item):
				elem.append(item)
			else:
				if not isinstance(item, basestring):
					item = unicode(item)
				if len(elem):
					elem[-1].tail = (elem[-1].tail or "") + item
				else:
					elem.text = (elem.text or "") + item
				
		return elem

	def __getattr__(self, tag):
		return functools.partial(self, tag)

E = _E()

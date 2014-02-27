from sleekxmpp.xmlstream import ElementBase, ET

class EnvoyQueryFlag(ElementBase):
	namespace = "urn:envoy:mam:extended"
	name = "extended-support"
	plugin_attrib = "extended_support"
	interfaces = set(["extended_support"])
	is_extension = True
	
	def setup(self, xml):
		"""Don't create XML for the plugin."""
		self.xml = ET.Element('')
	
	def get_extended_support(self):
		print self.parent().xml.find('{%s}%s' % (self.namespace, self.name))
		return self.parent().xml.find('{%s}%s' % (self.namespace, self.name)) is not None

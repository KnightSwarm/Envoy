# Local imports
from .util import Singleton, LocalSingleton

# SleekXMPP
from sleekxmpp import Iq
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.handler.callback import Callback

@LocalSingleton
class Component(ComponentXMPP):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		
	def initialize(self, jid, host, port, password, conference_host, config_path):
		ComponentXMPP.__init__(self, jid, password, host, port)
		self.conference_host = "conference.%s" % host
		#self.identifier = id(self)
		self.host = host
		
		self.add_event_handler("forwarded_stanza", StanzaHandler.Instance(self.identifier).process)
		self.add_event_handler("groupchat_joined", MucHandler.Instance(self.identifier).process_join)
		self.add_event_handler("groupchat_left", MucHandler.Instance(self.identifier).process_leave)
		self.add_event_handler("groupchat_presence", MucHandler.Instance(self.identifier).process_presence)
		self.add_event_handler("session_start", self.start, threaded=True)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0059') # Result Set Management
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0082') # XMPP Date and Time Profiles
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		self.registerPlugin('xep_0313') # Message Archive Management
		
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).is_joined, 'is_joined_room')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).get_joined, 'get_joined_rooms')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).add_joined, 'add_joined_room')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).delete_joined, 'del_joined_room')
		
		# Log retrieval handling
		self["xep_0030"].add_feature("urn:xmpp:mam:tmp") # Register the MAM feature as being available
		self["xep_0030"].add_feature("urn:envoy:mam:extended") # Register extended (Envoy) MAM as available feature
		self.register_handler(Callback("MAM Query", MatchXPath("{%s}iq/{urn:xmpp:mam:tmp}query" % self.default_ns), LogRequestHandler.Instance(self.identifier).process))
		
		configuration = ConfigurationProvider.Instance(self.identifier)
		configuration.read(config_path)
		
		database = Database.Instance(self.identifier)
		database.initialize(configuration.mysql_hostname, configuration.mysql_username, configuration.mysql_password, configuration.mysql_database)
		
	def start(self, *args, **kwargs):
		# The following might be useful, if it is decided to re-add scheduled purging. This should not
		# be necessary in an optimal scenario, as everything would stay in sync as long as the
		# component is running.
		#self.scheduler.add("Purge Presences", 300, self._envoy_purge_presences, repeat=True)
		RoomSyncer.Instance(self.identifier).sync()
		AffiliationSyncer.Instance(self.identifier).sync()
		PresenceSyncer.Instance(self.identifier).sync()
		StatusSyncer.Instance(self.identifier).sync()
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.get(self.host)

"""
xmpp = EnvoyComponent("component.envoy.local", "127.0.0.1", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)
"""

from .db import Database
from .handlers import StanzaHandler, MucHandler, OverrideHandler, LogRequestHandler
from .providers import FqdnProvider, ConfigurationProvider
from .sync import PresenceSyncer, AffiliationSyncer, RoomSyncer, StatusSyncer
from .stanzas import EnvoyQueryFlag

from sleekxmpp.plugins.xep_0313 import MAM

#register_stanza_plugin(Iq, Query)
register_stanza_plugin(MAM, EnvoyQueryFlag)

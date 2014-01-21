# Local imports
from .util import Singleton, LocalSingleton

# SleekXMPP
from sleekxmpp.componentxmpp import ComponentXMPP

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
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).is_joined, 'is_joined_room')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).get_joined, 'get_joined_rooms')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).add_joined, 'add_joined_room')
		self['xep_0045'].api.register(OverrideHandler.Instance(self.identifier).delete_joined, 'del_joined_room')
		
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
from .handlers import StanzaHandler, MucHandler, OverrideHandler
from .providers import FqdnProvider, ConfigurationProvider
from .sync import PresenceSyncer, AffiliationSyncer, RoomSyncer

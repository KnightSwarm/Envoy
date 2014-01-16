# Local imports
from util.singleton import Singleton, LocalSingleton

from .handlers import StanzaHandler, MucHandler, OverrideHandler
from .providers import FqdnProvider
from .sync import PresenceSyncer, AffiliationSyncer, RoomSyncer

# SleekXMPP
from sleekxmpp.componentxmpp import ComponentXMPP

import uuid

reload(sys)
sys.setdefaultencoding('utf8')

@LocalSingleton
class Component(ComponentXMPP):
	def initialize(self, jid, host, port, password, conference_host):
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
		
	def start(self):
		# The following might be useful, if it is decided to re-add scheduled purging. This should not
		# be necessary in an optimal scenario, as everything would stay in sync as long as the
		# component is running.
		#self.scheduler.add("Purge Presences", 300, self._envoy_purge_presences, repeat=True)
		RoomSyncer.Instance(self.identifier).sync()
		AffiliationSyncer.Instance(self.identifier).sync()
		PresenceSyncer.Instance(self.identifier).sync()
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.get(self.host)[0]

xmpp = Component.Instance(uuid.uuid4())
xmpp.initialize("component.envoy.local", "envoy.local", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)

"""
xmpp = EnvoyComponent("component.envoy.local", "127.0.0.1", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)
"""

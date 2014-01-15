# Local imports
from util.singleton import Singleton, LocalSingleton

from .handlers import StanzaHandler, MucHandler
from .providers import FqdnProvider

# SleekXMPP
from sleekxmpp.componentxmpp import ComponentXMPP

reload(sys)
sys.setdefaultencoding('utf8')

@LocalSingleton
class Component(ComponentXMPP):
	def __init__(self, jid, host, port, password, conference_host):
		ComponentXMPP.__init__(self, jid, password, host, port)
		self.conference_host = "conference.%s" % host
		self.identifier = id(self)
		self.host = host
		
		self.add_event_handler("forwarded_stanza", handlers.StanzaHandler.Instance(self.identifier).process)
		self.add_event_handler("groupchat_joined", handlers.MucHandler.Instance(self.identifier).process_join)
		self.add_event_handler("groupchat_left", handlers.MucHandler.Instance(self.identifier).process_leave)
		self.add_event_handler("groupchat_presence", handlers.MucHandler.Instance(self.identifier).process_presence)
		self.add_event_handler("session_start", self._envoy_start, threaded=True)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		
		self['xep_0045'].api.register(self._envoy_is_joined_room, 'is_joined_room')
		self['xep_0045'].api.register(self._envoy_get_joined_rooms, 'get_joined_rooms')
		self['xep_0045'].api.register(self._envoy_add_joined_room, 'add_joined_room')
		self['xep_0045'].api.register(self._envoy_del_joined_room, 'del_joined_room')
		
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.get(self.host)[0]

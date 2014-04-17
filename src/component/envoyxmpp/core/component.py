# Local imports
from .util import Singleton, LocalSingleton

# SleekXMPP
from sleekxmpp import Iq, Message
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.handler.callback import Callback

import time

@LocalSingleton
class Component(ComponentXMPP):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		
	def initialize(self, jid, host, port, password, conference_host, config_path):
		ComponentXMPP.__init__(self, jid, password, host, port)
		self.conference_host = "conference.%s" % host
		#self.identifier = id(self)
		self.host = host
		self.joined_rooms = [] # Internal cache for state keeping of own (component) room presences
		
		self.add_event_handler("forwarded_stanza", StanzaHandler.Instance(self.identifier).process)
		self.add_event_handler("groupchat_joined", MucHandler.Instance(self.identifier).process_join)
		self.add_event_handler("groupchat_left", MucHandler.Instance(self.identifier).process_leave)
		self.add_event_handler("groupchat_presence", MucHandler.Instance(self.identifier).process_presence)
		self.add_event_handler("zmq_event", ZeromqEventHandler.Instance(self.identifier).process)
		self.add_event_handler("resolve_finished", ResolveHandler.Instance(self.identifier).callback)
		self.add_event_handler("session_start", self.start, threaded=True)
		self.add_event_handler("disconnected", self.cleanup)
		self.add_event_handler("kill", self.cleanup)
		
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0059') # Result Set Management
		self.registerPlugin('xep_0060') # PubSub
		self.registerPlugin('xep_0082') # XMPP Date and Time Profiles
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0297') # Stanza forwarding
		self.registerPlugin('xep_0313') # Message Archive Management
		
		override_handler = OverrideHandler.Instance(self.identifier)
		
		self['xep_0045'].api.register(override_handler.is_joined, 'is_joined_room')
		self['xep_0045'].api.register(override_handler.get_joined, 'get_joined_rooms')
		self['xep_0045'].api.register(override_handler.add_joined, 'add_joined_room')
		self['xep_0045'].api.register(override_handler.delete_joined, 'del_joined_room')
		
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
		logger = ApplicationLogger.Instance(self.identifier)
		
		# Only now that the component is connected, will we start accepting messages over the
		# ZeroMQ event socket.
		self.event_thread = ZeromqEventThread.Instance(self.identifier)
		self.event_thread.start()
		
		# ... and here we start the preview resolver queue; or rather, the thread for it.
		self.queue = ResolverQueue.Instance(self.identifier)
		self.queue.start()
		
		logger.debug("Launched ResolverQueue thread")
		
		# Synchronize all data...
		RoomSyncer.Instance(self.identifier).sync()
		AffiliationSyncer.Instance(self.identifier).sync()
		PresenceSyncer.Instance(self.identifier).sync()
		StatusSyncer.Instance(self.identifier).sync()
		VcardSyncer.Instance(self.identifier).sync()
		
	def cleanup(self, *args, **kwargs):
		logger = ApplicationLogger.Instance(self.identifier)
		
		# Shut down threads, so we can recreate new ones later.
		try:
			self.event_thread.stop = True
			self.queue.stop = True
		except AttributeError, e:
			# Never mind, we apparently never connected.
			return
		
		# Statekeeping.
		last_event_thread = False
		last_queue = False
		
		while True:
			if self.event_thread.stopped == True and last_event_thread == False:
				last_event_thread = True
				logger.info("ZeroMQ event thread cleaned up.")
				ZeromqEventThread.RemoveInstance(self.identifier)
				
			if self.queue.stopped == True and last_queue == False:
				last_queue = True
				logger.info("Queue resolver thread cleaned up.")
				ResolverQueue.RemoveInstance(self.identifier)
				
			if self.event_thread.stopped and self.queue.stopped:
				break
				
			time.sleep(0.5)
					
	def get_fqdn(self):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		return fqdn_provider.get(self.host)

"""
xmpp = EnvoyComponent("component.envoy.local", "127.0.0.1", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)
"""

from .db import Database
from .handlers import StanzaHandler, MucHandler, OverrideHandler, LogRequestHandler, ZeromqEventHandler, ResolveHandler
from .providers import FqdnProvider, ConfigurationProvider
from .sync import PresenceSyncer, AffiliationSyncer, RoomSyncer, StatusSyncer, VcardSyncer
from .stanzas import EnvoyQueryFlag, ResolverResponse, ResolverResponseData
from .zeromq import ZeromqEventThread
from .queues import ResolverQueue
from .loggers import ApplicationLogger

from sleekxmpp.plugins.xep_0313 import MAM

#register_stanza_plugin(Iq, Query)
register_stanza_plugin(MAM, EnvoyQueryFlag)
register_stanza_plugin(Message, ResolverResponse)
register_stanza_plugin(ResolverResponse, ResolverResponseData)

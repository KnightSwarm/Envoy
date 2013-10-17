import time, sleekxmpp
from sleekxmpp import ClientXMPP
from sleekxmpp.util import Queue, QueueEmpty
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

q = PyQueue();

class Client(ClientXMPP):
	def __init__(self, username, fqdn, password):
		self._jid = "%s@%s" % (username, fqdn)
		self.conference_host = "conference.%s" % fqdn
		ClientXMPP.__init__(self, self._jid, password)
		
		self.add_event_handler("session_start", self.session_start)
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0048') # Bookmarks
		self.registerPlugin('xep_0199') # XMPP Ping
		
	def session_start(self, event):
		self.get_roster()
		self.send_presence()
		
		console.log("CONNECTED!")
		
		self._update_room_list()
		
		# TODO: Load bookmarks
		## console.log(self['xep_0048'].get_bookmarks())
		
	def _update_room_list(self):
		rooms = self['xep_0045'].get_rooms(ifrom=self.boundjid, jid=self.conference_host)['disco_items']['items']
		
		for room_jid, room_node, room_name in rooms:
			q.put({"type": "roomlist_add", "data": {
				"name": room_name,
				"jid": room_jid,
				"icon": "comments"
			}})
			
		console.log("Room list updated...")
	
def dom_load():
	xmpp = Client("testuser", "envoy.local", "testpass")
	xmpp.connect()
	xmpp.process(block=False)

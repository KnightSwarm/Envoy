import time, sleekxmpp
from sleekxmpp import ClientXMPP
from sleekxmpp.util import Queue, QueueEmpty
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

q = PyQueue()

class Client(ClientXMPP):
	def __init__(self, username, fqdn, password, queue):
		self._jid = "%s@%s" % (username, fqdn)
		self.conference_host = "conference.%s" % fqdn
		ClientXMPP.__init__(self, self._jid, password)
		
		self.q = queue
		
		self.add_event_handler("session_start", self.session_start)
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0048') # Bookmarks
		self.registerPlugin('xep_0199') # XMPP Ping
		
		self.add_event_handler("groupchat_joined", self.on_groupchat_joined)
		self.add_event_handler("groupchat_left", self.on_groupchat_left)
		self.add_event_handler("groupchat_presence", self.on_groupchat_presence)
		
		self.all_rooms = {}
		self.joined_rooms = []
		
	def session_start(self, event):
		self.get_roster()
		self.send_presence()
		
		console.log("CONNECTED!")
		
		self._update_room_list()
		
		# TODO: Load bookmarks
		## console.log(self['xep_0048'].get_bookmarks())
		
	def _update_room_list(self):
		rooms = self['xep_0045'].get_rooms(ifrom=self.boundjid, jid=self.conference_host)['disco_items']['items']
		
		new_rooms = []
		for room_jid, room_node, room_name in rooms:
			new_rooms.append(room_jid)
			
			if room_jid not in self.all_rooms:
				# Room was created
				self.all_rooms[room_jid] = room_name
				self.q.put({"type": "roomlist_add", "data": [{
					"type": "room",
					"name": room_name,
					"jid": room_jid,
					"icon": "comments"
				}]})
				
		for room_jid in self.all_rooms.keys():
			if room_jid not in new_rooms:
				# Room was removed
				del self.all_rooms[room_jid]
				self.q.put({"type": "roomlist_remove", "data": [{
					"jid": room_jid
				}]})
					
		console.log("Room list updated...")
	
	def on_groupchat_joined(self, stanza):
		room_jid = stanza["from"].bare
		self.signal_join(room_jid)
		
	def on_groupchat_presence(self, stanza):
		nickname = stanza["from"].resource
		room_jid = stanza["from"].bare
		# check for 100 (meaning non-anonymous)
		real_jid = str(stanza["muc"]["jid"])
		role = stanza["muc"]["role"]
		affiliation = stanza["muc"]["affiliation"]
		status = stanza["type"]
		
		# Make sure to signal the join first, so that we don't try to process
		# presences when the room UI isn't ready yet.
		self.signal_join(room_jid)
		
		self.q.put({"type": "user_status", "data": {
			"jid": real_jid,
			"status": status
		}})
		
		self.q.put({"type": "user_presence", "data": {
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nickname,
			"status": status,
			"role": role,
			"affiliation": affiliation
		}})
	
	def signal_join(self, room_jid):
		try:
			room_name = self.all_rooms[room_jid]
		except KeyError, e:
			# We are not aware of this room yet...
			# TODO: Fetch details
			room_name = room_jid
		
		if room_jid not in self.joined_rooms:
			self.joined_rooms.append(room_jid)
			self.q.put({"type": "joinlist_add", "data": [{
				"type": "room",
				"name": room_name,
				"jid": room_jid,
				"icon": "comments"
			}]})
			
	def on_groupchat_left(self, stanza):
		room_jid = stanza["from"].bare
		nickname = stanza["from"].resource
		
		if "110" in [status["code"] for status in stanza["muc"]["statuses"]]:
			self.joined_rooms.remove(room_jid)
			self.q.put({"type": "joinlist_remove", "data":[{
				"jid": room_jid
			}]})
	
class TideBackend(object):
	def __init__(self, username, fqdn, password, queue):
		self.username = username
		self.fqdn = fqdn
		self.password = password
		self.q = queue
		self.client = Client(username, fqdn, password, queue)
		self.client.connect()
		self.client.process(block=False)
		
	def join_room(self, room_jid):
		self.client['xep_0045'].join(room_jid, self.username)
		#self.q.put({"type": "roomlist_add", "data": [{
		#	"type": "room",
		#	"name": "Newly joined room",
		#	"jid": room_jid,
		#	"icon": "comments"
		#}]})
		
	def leave_room(self, room_jid):
		self.client['xep_0045'].leave(room_jid)
		
	def get_vcard(self, jid):
		pass
		
	def send_group_message(self, message, room_jid):
		pass
		
	def send_private_message(self, message, recipient):
		pass
		
	def change_status(self, status):
		pass
		
	def change_topic(self, room_jid, topic):
		pass
		
	def update_room_list(self):
		self.client._update_room_list()
		
def dom_load():
	console.log("Initialized as TideSDK client.");
	window.backend = TideBackend("testuser", "envoy.local", "testpass", q)

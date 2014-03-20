import time, sleekxmpp
from sleekxmpp import ClientXMPP
from sleekxmpp.util import Queue, QueueEmpty
import logging, time, calendar
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

q = PyQueue()

class Client(ClientXMPP):
	def __init__(self, username, fqdn, password, queue):
		self.q = queue
		
		self._jid = "%s@%s" % (username, fqdn)
		self.conference_host = "conference.%s" % fqdn
		
		try:
			ClientXMPP.__init__(self, self._jid, password)
		except ValueError, e:
			# Invalid data (JID?) specified
			self.q.put({"type": "login_failed", "data": {"error_type": "value"}})
		
		self.add_event_handler("session_start", self.session_start)
		self.add_event_handler("no_auth", self.authentication_failed)
		self.registerPlugin('xep_0030') # Service Discovery
		self.registerPlugin('xep_0004') # Data Forms
		self.registerPlugin('xep_0045') # MUC
		self.registerPlugin('xep_0048') # Bookmarks
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0203') # Delayed delivery
		
		self.add_event_handler("groupchat_joined", self.on_groupchat_joined)
		self.add_event_handler("groupchat_left", self.on_groupchat_left)
		self.add_event_handler("groupchat_presence", self.on_groupchat_presence)
		self.add_event_handler("groupchat_message", self.on_groupchat_message)
		
		self.all_rooms = {}
		self.joined_rooms = []
		self.nicknames = defaultdict(dict)
		
	def session_start(self, event):
		self.get_roster()
		self.send_presence()
		
		self.q.put({"type": "login_success", "data": {}})
		
		self._update_room_list()
		
		# TODO: Load bookmarks
		## console.log(self['xep_0048'].get_bookmarks())
		
	def authentication_failed(self, event):
		self.q.put({"type": "login_failed", "data": {"error_type": "auth"}})
		
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
		
		# Store nickname and real JID internally
		self.nicknames[room_jid][nickname] = real_jid
		
		# Make sure to signal the join first, so that we don't try to process
		# presences when the room UI isn't ready yet.
		self.signal_join(room_jid)
		
		# TODO: Also capture non-groupchat presence updates?
		if status != "unavailable":
			self.q.put({"type": "user_status", "data": {
				"jid": real_jid,
				"status": status,
				"timestamp": time.time()
			}})
		
		self.q.put({"type": "user_presence", "data": {
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nickname,
			"fullname": nickname, # FIXME: vCard data!
			"status": status,
			"role": role,
			"affiliation": affiliation,
			"timestamp": time.time()
		}})
		
	def on_groupchat_message(self, stanza):
		room_jid = stanza["from"].bare
		nickname = stanza["from"].resource
			
		'''  FIXME: This is currently broken due to a bug in the XEP-0203 plugin. As a temporary workaround,
		     we will just check if the timestamp falls within the first 2 days of epoch; if so, replace with current time.
		try:
			timestamp = int(time.mktime(stanza["delay"]["stamp"].timetuple()))
			delayed = True
		except KeyError, e:
			# This wasn't a delayed message
			timestamp = int(time.time())
			delayed = False
		'''
		
		## START HACK
		timestamp = int(calendar.timegm(stanza["delay"]["stamp"].timetuple()))
		delayed = True
		
		if timestamp < (60 * 60 * 24 * 2):
			timestamp = int(time.time())
			delayed = False
		## END HACK
		
		try:
			real_jid = self.nicknames[room_jid][nickname]
		except KeyError, e:
			# This is only a problem if the message is real-time; the user should really be in the room then.
			if delayed == True:
				logging.debug("Delayed message from %s, could not associate real JID." % stanza["from"])
				real_jid = ""
			else:
				logging.error("No known real JID for %s!" % stanza["from"])
				return
			
		self.q.put({"type": "receive_message", "data": {
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nickname,
			"fullname": nickname, # FIXME: vCard data!
			"body": stanza["body"],
			"timestamp": timestamp
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
		self.client.send_message(mto=room_jid, mbody=message, mtype="groupchat")
		
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
	
def start_client(username, fqdn, password):
	window.backend = TideBackend(username, fqdn, password, q)

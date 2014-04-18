import time, sleekxmpp, sys, os
from sleekxmpp import ClientXMPP, Message
from sleekxmpp.util import Queue, QueueEmpty
import logging, time, calendar
from collections import defaultdict
from sleekxmpp.plugins.xep_0048 import Bookmarks
from sleekxmpp.exceptions import IqError
from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin
from sleekxmpp.xmlstream.matcher.xpath import MatchXPath
from sleekxmpp.xmlstream.handler.callback import Callback

def get_application_data_path():
	# Source: https://stackoverflow.com/a/1088459/1332715
	APPNAME = "EnvoyClient"

	if sys.platform == 'darwin':
		from AppKit import NSSearchPathForDirectoriesInDomains
		# http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
		# NSApplicationSupportDirectory = 14
		# NSUserDomainMask = 1
		# True for expanding the tilde into a fully qualified path
		return os.path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], APPNAME)
	elif sys.platform == 'win32':
		return os.path.join(os.environ['APPDATA'], APPNAME)
	else:
		return os.path.expanduser(os.path.join("~", "." + APPNAME))

try:
	os.makedirs(get_application_data_path())
except OSError, e:
	pass # Already exists

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", filename=os.path.join(get_application_data_path(), "client.log"))

q = PyQueue()

class ResolverResponse(ElementBase):
	namespace = "urn:envoy:resolver:response"
	name = "response"
	plugin_attrib = "resolver_response"
	interfaces = set(["html", "ref"])
	sub_interfaces = set(["html"])

class ResolverResponseData(ElementBase):
	namespace = "urn:envoy:resolver:response"
	name = "data"
	plugin_attrib = "data"
	interfaces = set(["title", "image", "description", "statistics"])
	sub_interfaces = set(["title", "image", "description", "statistics"])

register_stanza_plugin(Message, ResolverResponse)
register_stanza_plugin(ResolverResponse, ResolverResponseData)

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
		self.registerPlugin('xep_0048', {"auto_join": True}) # Bookmarks
		self.registerPlugin('xep_0054') # vcard-temp
		self.registerPlugin('xep_0199') # XMPP Ping
		self.registerPlugin('xep_0203') # Delayed delivery
		
		self.add_event_handler("groupchat_joined", self.on_groupchat_joined)
		self.add_event_handler("groupchat_left", self.on_groupchat_left)
		self.add_event_handler("groupchat_presence", self.on_groupchat_presence)
		self.add_event_handler("groupchat_message", self.on_groupchat_message)
		self.add_event_handler("message", self.on_message)
		
		self.register_handler(Callback("Resolver Response", MatchXPath("{%s}message/{urn:envoy:resolver:response}response" % self.default_ns), self._on_preview))
		logging.debug("{%s}message/{urn:envoy:resolver:response}response" % self.default_ns)
		
		self.all_rooms = {}
		self.joined_rooms = []
		self.nicknames = defaultdict(dict)
		
	def session_start(self, event):
		self.get_roster()
		self.send_presence()
		
		self.q.put({"type": "login_success", "data": {}})
		
		self._update_room_list()
		self.scheduler.add("Update roomlist", 300, self._update_room_list, repeat=True)
		
		# TODO: Load bookmarks
		## window.log(self['xep_0048'].get_bookmarks())
		
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
					
		window.log("Room list updated...")
	
	def _on_preview(self, stanza):
		# A resolver preview was received. We will only process it if the
		# origin is the component, to prevent third-party XSS attacks.
		logging.debug("PREVIEW START")
		logging.debug(str(stanza["from"]))
		if str(stanza["from"]) != "component.envoy.local" and stanza["from"].resource != "Envoy_Component": #FIXME: This should not be hardcoded.
			logging.warning("Received resolver preview from entity that is not the Envoy component; ignoring.")
			return
		logging.debug("PREVIEW")
		logging.debug(stanza)
		self.q.put({"type": "preview", "data": {
			"html": stanza["resolver_response"]["html"],
			"message_id": stanza["resolver_response"]["ref"]
		}})
	
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
		message_id = stanza["id"]
			
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
		
		if stanza["delay"]._get_attr("stamp") == "" or timestamp < (60 * 60 * 24 * 2):
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
			"id": message_id,
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nickname,
			"fullname": nickname, # FIXME: vCard data!
			"body": stanza["body"],
			"timestamp": timestamp,
			"preview": ""
		}})
		
	def on_message(self, stanza):
		if stanza["type"] == "groupchat":
			return # Not interested, MUC message.
		
		jid = str(stanza["from"])
		message_id = stanza["id"]
		
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
		
		if stanza["delay"]._get_attr("stamp") == "" or timestamp < (60 * 60 * 24 * 2):
			timestamp = int(time.time())
			delayed = False
		## END HACK
		
		self.q.put({"type": "receive_private_message", "data": {
			"id": message_id,
			"jid": jid,
			"body": stanza["body"],
			"timestamp": timestamp,
			"preview": ""
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
		# FIXME: Remove bookmark!
		self.client['xep_0045'].leave(room_jid)
		
	def bookmark_room(self, room_jid):
		logging.debug("Bookmarking %s..." % room_jid)
		stanza = self.client["xep_0048"].get_bookmarks()
		stanza["private"]["bookmarks"].add_conference(room_jid, self.username, autojoin=True)
		new_iq = self.client.make_iq_set(ito=stanza["from"], iq=stanza)
		new_iq.send()
		logging.debug("Bookmark for %s set." % room_jid)
		
	def remove_bookmark(self, jid):
		logging.debug("Removing bookmark for %s..." % jid)
		# Since SleekXMPP appears to offer no way to remove bookmarks... we'll have
		# to iterate over all of them, and simply create a new bookmark storage set with
		# the ones we -don't- want to remove.
		# TODO: Race conditions?
		stanza = Bookmarks()
		for bookmark in self.client["xep_0048"].get_bookmarks()["private"]["bookmarks"]:
			if bookmark["jid"] != jid:
				stanza.append(bookmark)
		self.client["xep_0048"].set_bookmarks(stanza)
		logging.debug("Bookmark for %s removed." % jid)
		
	def get_vcard(self, jid):
		# This returns a limited set of vCard information, not the full vCard.
		try:
			vcard = self.client["xep_0054"].get_vcard(jid)
		except IqError, e:
			return {
				"jid": jid,
				"full_name": jid.split("@")[0],
				"job_title": "",
				"nickname": jid.split("@")[0],
				"mobile_number": "",
				"email_address": ""
			} # For some reason we couldn't get vcard data. FIXME: Logging!
		
		return {
			"jid": jid,
			"full_name": vcard["vcard_temp"]["FN"],
			"job_title": vcard["vcard_temp"]["TITLE"],
			"nickname": vcard["vcard_temp"]["NICKNAME"],
			"mobile_number": vcard["vcard_temp"]["TEL"]["NUMBER"],
			"email_address": vcard["vcard_temp"]["EMAIL"]["USERID"]
		}
		
	def send_group_message(self, message, room_jid):
		self.client.send_message(mto=room_jid, mbody=message, mtype="groupchat")
		
	def send_private_message(self, message, recipient_jid):
		self.client.send_message(mto=recipient_jid, mbody=message, mtype="chat")
		
	def set_affiliation(self, room, jid, affiliation):
		try:
			self.client["xep_0045"].set_affiliation(room, jid, affiliation)
		except IqError, e:
			pass
		
	def change_status(self, status):
		pass
		
	def change_topic(self, room_jid, topic):
		pass
		
	def update_room_list(self):
		self.client._update_room_list()
		
def dom_load():
	window.log("Initialized as TideSDK client.");
	
def start_client(username, fqdn, password):
	window.backend = TideBackend(username, fqdn, password, q)

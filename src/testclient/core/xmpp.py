# Local imports
import log, application

import sleekxmpp

class Client(sleekxmpp.ClientXMPP):
	def __init__(self, jid, password):
		log.info("Logging in...")
		
		sleekxmpp.ClientXMPP.__init__(self, jid, password)
		
		self._jid = jid
		self._password = password
		
		self.add_event_handler("session_start", self.on_session_start)
		self.add_event_handler("message", self.on_message)
		
	def on_session_start(self, event):
		self.send_presence()
		self.get_roster()
		
		log.info("Logged in as %s." % self._jid)
		
	def on_message(self, message):
		if message['type'] == "chat":
			application.main_application.on_muc_message(message)
		elif message['type'] == "normal":
			application.main_application.on_private_message(message)

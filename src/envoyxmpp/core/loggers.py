from .util import Singleton, LocalSingleton, LocalSingletonBase

from datetime import datetime
import logging, uuid

@LocalSingleton
class EventLogger(LocalSingletonBase):
	presence_types = {
		"login": 1,
		"disconnect": 2,
		"join": 3,
		"leave": 4
	}  # ???
	
	event_types = {
		"message": 1,
		"pm": 2,
		"status": 3,
		"presence": 4,
		"topic": 5
	}
	
	def log_message(self, sender, recipient, type_, body, stanza):
		database = Database.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		row = Row()
		row["Id"] = stanza["mam_archived"]["id"] # Use the UUID that mod_mam_pretend assigned for us
		row["Date"] = datetime.now()
		row["Sender"] = user_provider.normalize_jid(sender)
		row["Recipient"] = user_provider.normalize_jid(recipient)
		row["Type"] = self.event_number(type_)
		row["Message"] = body
		row["Stanza"] = str(stanza)
		row["FqdnId"] = component.get_fqdn().id
		database["log_messages"].append(row)
		
	def log_event(self, sender, recipient, type_, event, stanza, extra=None):
		database = Database.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		row = Row()
		row["Id"] = str(uuid.uuid4()) # Generate a new UUID, mod_mam_pretend doesn't deal with anything that isn't a message
		row["Date"] = datetime.now()
		row["Sender"] = user_provider.normalize_jid(sender)
		row["Recipient"] = user_provider.normalize_jid(recipient)
		row["Type"] = self.event_number(type_)
		row["Event"] = self.presence_number(event)
		row["Extra"] = extra
		row["Stanza"] = str(stanza)
		row["FqdnId"] = component.get_fqdn().id
		database["log_events"].append(row)
		
	def presence_string(self, value):
		user_provider = UserProvider.Instance(self.identifier)
		
		reversed_presences = dict(zip(self.presence_types.values(), self.presence_types.keys()))
		
		try:
			return reversed_presences[value]
		except KeyError, e:
			return user_provider.status_string(value)
		
	def presence_number(self, value):
		user_provider = UserProvider.Instance(self.identifier)
		
		try:
			return self.presence_types[value]
		except KeyError, e:
			return user_provider.status_number(value)
		
	def event_string(self, value):
		reversed_types = dict(zip(self.event_types.values(), self.event_types.keys()))
		return reversed_types[value]
		
	def event_number(self, value):
		return self.event_types[value]

@LocalSingleton
class ApplicationLogger(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		logging.basicConfig(filename="/etc/envoy/envoy.log", level=logging.DEBUG, format='%(levelname)-8s %(message)s')
		
	def debug(self, message, *args, **kwargs):
		logging.debug(message, *args, **kwargs)
		
	def info(self, message, *args, **kwargs):
		logging.info(message, *args, **kwargs)
		
	def warning(self, message, *args, **kwargs):
		logging.warning(message, *args, **kwargs)
		
	def error(self, message, *args, **kwargs):
		logging.error(message, *args, **kwargs)
		
	def critical(self, message, *args, **kwargs):
		logging.critical(message, *args, **kwargs)
		
from .db import Database, Row
from .providers import UserProvider
from .component import Component

from .util import Singleton, LocalSingleton, LocalSingletonBase

from .db import Database, Row
from .providers import UserProvider

from datetime import datetime
import logging

@LocalSingleton
class EventLogger(LocalSingletonBase):
	def log_message(self, sender, recipient, type_, body):
		database = Database.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		row = Row()
		row["Date"] = datetime.now()
		row["Sender"] = user_provider.normalize_jid(sender)
		row["Recipient"] = user_provider.normalize_jid(recipient)
		row["Type"] = type_
		row["Message"] = body
		database["log_messages"].append(row)
		
	def log_event(self, sender, recipient, type_, event, extra=None):
		database = Database.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		
		row = Row()
		row["Date"] = datetime.now()
		row["Sender"] = user_provider.normalize_jid(sender)
		row["Recipient"] = user_provider.normalize_jid(recipient)
		row["Type"] = type_
		row["Event"] = event
		row["Extra"] = extra
		database["log_events"].append(row)

@LocalSingleton
class ApplicationLogger(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		logging.basicConfig(filename="/etc/envoy/envoy.log", level=logging.DEBUG, format='%(levelname)-8s %(message)s')
		
	def debug(message, *args, **kwargs):
		logging.debug(message, *args, **kwargs)
		
	def info(message, *args, **kwargs):
		logging.info(message, *args, **kwargs)
		
	def warning(message, *args, **kwargs):
		logging.warning(message, *args, **kwargs)
		
	def error(message, *args, **kwargs):
		logging.error(message, *args, **kwargs)
		
	def critical(message, *args, **kwargs):
		logging.critical(message, *args, **kwargs)
		

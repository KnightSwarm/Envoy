from .util import Singleton, LocalSingleton, LocalSingletonBase
from .db import Row

from datetime import datetime

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
		
	def log_event(self, sender, recipient, type_, event, extra):
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

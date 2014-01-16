from .util import LocalSingleton, LocalSingletonBase

@LocalSingleton
class MessageSender(LocalSingletonBase):
	def send(self, recipient=None, body=None):
		component = Component.Instance(self.identifier)
		
		component.send_message(mto=sender, mbody=body)

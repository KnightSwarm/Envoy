import logging

from component import Component

def on_login(user):
	print "%s just logged in." % user

def on_logout(user, reason):
	print "%s just disconnected with reason '%s'." % (user, reason)

def on_ping(user):
	print "%s just pinged." % user

def on_status(user, status, message):
	print "%s just changed their status to %s (%s)." % (user, status, message)

def on_join(user, room):
	print "%s joined %s." % (user, room)
	
def on_group_message(user, room, body):
	print "%s sent channel message to %s: '%s'" % (user, room, body)
	
def on_private_message(sender, recipient, body):
	print "%s sent private message to %s: '%s'" % (sender, recipient, body)
	
def on_topic_change(user, room, topic):
	print "%s changed topic for %s to '%s'" % (user, room, topic)

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

xmpp = Component("component.envoy.local", "envoy.local", 5347, "password")
xmpp.register_event("login", on_login)
xmpp.register_event("logout", on_logout)
xmpp.register_event("ping", on_ping)
xmpp.register_event("status", on_status)
xmpp.register_event("join", on_join)
xmpp.register_event("group_message", on_group_message)
xmpp.register_event("private_message", on_private_message)
xmpp.register_event("topic_change", on_topic_change)
xmpp.connect()
xmpp.process(block=True)

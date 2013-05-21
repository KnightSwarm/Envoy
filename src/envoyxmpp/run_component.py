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

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

xmpp = Component("component.envoy.local", "envoy.local", 5347, "password")
xmpp.register_event("login", on_login)
xmpp.register_event("logout", on_logout)
xmpp.register_event("ping", on_ping)
xmpp.register_event("status", on_status)
xmpp.register_event("join", on_join)
xmpp.connect()
xmpp.process(block=True)

from component import Component

def on_login(user):
	print "%s just logged in." % user

def on_logout(user, reason):
	print "%s just disconnected with reason '%s'." % (user, reason)

def on_ping(user):
	print "%s just pinged." % user

def on_status(user, status, message):
	print "%s just changed their status to %s (%s)." % (user, status, message)

xmpp = Component("component.envoy.local", "envoy.local", 5347, "password")
xmpp.register_event("login", on_login)
xmpp.register_event("logout", on_logout)
xmpp.register_event("ping", on_ping)
xmpp.register_event("status", on_status)
xmpp.connect()
xmpp.process(block=True)

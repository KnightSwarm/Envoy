from component import Component

xmpp = Component("component.envoy.local", "envoy.local", 5347, "password")
xmpp.connect()
xmpp.process(block=True)

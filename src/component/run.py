import uuid, sys

from envoyxmpp.core.component import Component

import logging
logging.basicConfig(filename="/etc/envoy/envoy.log", level=logging.DEBUG, format='%(levelname)-8s %(message)s')

reload(sys)
sys.setdefaultencoding('utf8')

xmpp = Component.Instance(uuid.uuid4())
print "created"
xmpp.initialize("component.envoy.local", "envoy.local", 5347, "password", "conference.envoy.local", "/vagrant/src/config.json")
print "initialized"
xmpp.connect()
print "connected"
xmpp.process(block=True)
print "processing finished"

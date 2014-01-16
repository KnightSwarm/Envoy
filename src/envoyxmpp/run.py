import uuid, sys

from core.component import Component

reload(sys)
sys.setdefaultencoding('utf8')

xmpp = Component.Instance(uuid.uuid4())
xmpp.initialize("component.envoy.local", "envoy.local", 5347, "password", "conference.envoy.local")
xmpp.connect()
xmpp.process(block=True)

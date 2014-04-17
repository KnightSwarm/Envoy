import uuid, sys, json

from envoyxmpp.core.component import Component

import logging
logging.basicConfig(filename="/var/log/envoy/envoy.log", level=logging.DEBUG, format='%(levelname)-8s %(message)s')

reload(sys)
sys.setdefaultencoding('utf8')

with open("/etc/envoy/config.json", "r") as config_file:
	config = json.loads(config_file.read())["xmpp_component"]

xmpp = Component.Instance(uuid.uuid4())
xmpp.initialize(config["jid"], config["fqdn"], config["port"], config["password"], "conference.%s" % config["fqdn"], "/etc/envoy/config.json")
xmpp.connect()
xmpp.process(block=True)

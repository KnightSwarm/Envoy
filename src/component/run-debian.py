#!/usr/bin/env python2

import uuid, sys, json, oursql, os, base64

from envoyxmpp.core.component import Component
from envoyxmpp.core.util import pbkdf2_sha512

import logging
logging.basicConfig(filename="/var/log/envoy/envoy.log", level=logging.DEBUG, format='%(levelname)-8s %(message)s')

reload(sys)
sys.setdefaultencoding('utf8')

def secure_random_string(length):
	needed_bytes = length / 4 * 3
	
	with open("/dev/urandom", "r") as random:
		bytes_ = random.read(needed_bytes)
		
	return base64.b64encode(bytes_).replace("/", "_").replace("+", "-")

with open("/etc/envoy/config.json", "r") as config_file:
	config = json.loads(config_file.read())

# Initial configuration
try:
	with open("/etc/envoy/init.dat", "r") as init_file:
		fqdn, username, password = [line.strip() for line in init_file.read().splitlines()]
		
	api_id = secure_random_string(16)
	api_key= secure_random_string(24)
		
	sql = oursql.connect(host=config["database"]["hostname"], user=config["database"]["username"], passwd=config["database"]["password"], db=config["database"]["database"], autoreconnect=True)
	cur = sql.cursor()
	
	# Import the table structure...
	with open("/usr/share/doc/envoy/structure.sql", "r") as structure_file:
		for statement in structure_file.read().split(";"):
			if statement.strip() == "":
				continue
			cur.execute(statement.strip(), plain_query=True)
		
	digest, salt, rounds = pbkdf2_sha512(password)
	
	cur.execute("INSERT INTO users (`Username`, `Fqdn`, `Hash`, `Salt`, `Active`, `FqdnId`) VALUES (?, ?, ?, ?, 1, 1)",
	            (username, fqdn, base64.b64encode(digest), base64.b64encode(salt)))
	            
	cur.execute("INSERT INTO fqdns (`UserId`, `Fqdn`, `Name`, `Description`) VALUES (1, ?, ?, '')", (fqdn, fqdn)) 
	cur.execute("INSERT INTO user_permissions (`UserId`, `FqdnId`, `Type`) VALUES (1, 1, 150)")
	cur.execute("INSERT INTO api_keys (`UserId`, `Type`, `Description`, `ApiId`, `ApiKey`) VALUES (0, 0, 'Master key', ?, ?)", (api_id, api_key))
	cur.execute("INSERT INTO api_permissions (`ApiKeyId`, `FqdnId`, `Type`) VALUES (1, 0, 200)")
	
	sql.close()
	
	with open("/etc/envoy/master-api-key", "w") as key_file:
		key_file.write("%s\n%s" % (api_id, api_key))
	
	os.remove("/etc/envoy/init.dat")
	
	print "Initialized database."
except IOError, e:
	pass # Initialization file doesn't exist. No need to initialize anything, apparently.
except oursql.IntegrityError, e:
	pass # The database was apparently already configured.

xmpp = Component.Instance(uuid.uuid4())
xmpp.initialize(config["xmpp_component"]["jid"], config["xmpp_component"]["fqdn"], config["xmpp_component"]["port"], config["xmpp_component"]["password"], "conference.%s" % config["xmpp_component"]["fqdn"], "/etc/envoy/config.json")
xmpp.connect()
xmpp.process(block=True)

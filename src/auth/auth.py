#!/usr/bin/python

import sys, logging, struct, oursql, json, os, base64
import envoyxmpp.core.hash

sys.stderr = open("/etc/envoy/extauth/extauth_err.log", "a")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", filename="/etc/envoy/extauth/extauth.log", filemode="a")

class EjabberdInputError(Exception):
	def __init__(self, value):
		self.value = value
		
	def __str__(self):
		return repr(self.value)

def get_relative_path(path):
	my_path = os.path.dirname(os.path.abspath(__file__))
	return os.path.normpath(os.path.join(my_path, path))

def ejabberd_read():
	logging.debug("trying to read 2 bytes from ejabberd...")
	
	try:
		header = sys.stdin.read(2)
	except IOError:
		logging.debug("ioerror encountered")
		return
	
	if len(header) is not 2:
		logging.error("ejabberd sent corrupt data")
		raise EjabberdInputError("Corrupt header received from ejabberd")
		
	logging.debug("received 2 bytes via stdin: %s" % header)
	
	(size,) = struct.unpack(">h", header)
	logging.debug("size of message: %d" % size)
	
	data = sys.stdin.read(size).split(":")
	logging.debug("data received: %s" % repr(data))
	
	return data

def ejabberd_write(response):
	logging.debug("Sending %s to ejabberd" % response)
	
	if response == True:
		data = struct.pack(">hh", 2, 1)
	else:
		data = struct.pack(">hh", 2, 0)
	
	logging.debug("Sent data is %#x %#x %#x %#x" % (ord(data[0]), ord(data[1]), ord(data[2]), ord(data[3])))
	
	sys.stdout.write(data)
	sys.stdout.flush()

def get_user(username, hostname):
	cursor = db.cursor()
	cursor.execute("SELECT `Id`, `Username`, `Fqdn`, `Hash`, `Salt`, `Active` FROM users WHERE `Username` = ? AND `Fqdn` = ?", (username, hostname))
	result = cursor.fetchone()
	
	if result is None:
		logging.info("Invalid username specified (%s@%s)" % (username, hostname))
	
	return result

def user_exists(username, hostname):
	return (get_user(username, hostname) is not None)

def authenticate(username, hostname, password):
	user = get_user(username, hostname)
	
	if user is None:
		return False
	
	_id, _username, _fqdn, _hash, _salt, _active = user
	digest, _, _ = envoyxmpp.core.hash.pbkdf2_sha512(password, base64.b64decode(_salt))
	
	if digest == base64.b64decode(_hash):
		logging.debug("Successful authentication (%s@%s)" % (username, hostname))
		return True
	else:
		logging.info("Invalid password specified (%s@%s)" % (username, hostname))
		return False

def register(username, hostname, password):
	user = get_user(username, hostname)
	
	if user is not None:
		logging.info("Attempt to register account that already exists (%s@%s)" % (username, hostname))
		return False
		
	digest, salt, rounds = envoyxmpp.util.hash.pbkdf2_sha512(password)
	
	cur = db.cursor()
	cur.execute("INSERT INTO users (`Username`, `Fqdn`, `Hash`, `Salt`, `Active`, `FqdnId`) VALUES (?, ?, ?, ?, ?, 0)",
	            (username, hostname, base64.b64encode(digest), base64.b64encode(salt), 1))
	
	return True
	
def set_password(username, hostname, password):
	user = get_user(username, hostname)
	
	if user is None:
		logging.info("Attempted to set password for non-existent user (%s@%s)" % (username, hostname))
		return False
	
	_id, _username, _fqdn, _hash, _salt, _active = user
	digest, salt, rounds = envoyxmpp.util.hash.pbkdf2_sha512(password, salt=base64.b64decode(_salt))
	
	cur = db.cursor()
	cur.execute("UPDATE users SET `Hash` = ? WHERE `Id` = ?", (base64.b64encode(digest), _id))
	
	if cur.rowcount > 0:
		logging.info("Password changed (%s@%s)" % (username, hostname))
		return True
	else:
		logging.warn("Failed to set password for unknown reason (%s@%s)" % (username, hostname))
		return False
		
def remove_user(username, hostname):
	cur = db.cursor()
	cur.execute("DELETE FROM users WHERE `Username` = ? AND `Fqdn` = ?", (username, hostname))
	
	if cur.rowcount > 0:
		logging.info("Removed user (%s@%s)" % (username, hostname))
		return True
	else:
		logging.info("Attempted to remove non-existent user (%s@%s)" % (username, hostname))
		return False
	
def remove_user_safe(username, hostname, password):
	if authenticate(username, hostname, password):
		return remove_user(username, hostname)
	else:
		return False

configuration = json.load(open(get_relative_path("../config.json"), "r"))

db = oursql.connect(host=configuration['database']['hostname'], user=configuration['database']['username'], 
                    passwd=configuration['database']['password'], db=configuration['database']['database'],
                    autoreconnect=True)
                    
logging.debug("Connected to database on %s@%s" % (configuration['database']['username'], configuration['database']['hostname']))
logging.info("External authentication script started, waiting for ejabberd requests...")

while True:
	try:
		request = ejabberd_read()
	except EjabberdInputError, e:
		logging.warning("Exception occurred, exiting: %s" % e)
		break
	
	logging.debug("Requested operation: %s" % request[0])
	
	if request[0] == "auth":
		# username:hostname:password
		result = authenticate(request[1], request[2], request[3])
		logging.debug("Result of authentication call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "isuser":
		# username:hostname
		result = user_exists(request[1], request[2])
		logging.debug("Result of isuser call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "setpass":
		# username:hostname:password
		result = set_password(request[1], request[2], request[3])
		logging.debug("Result of setpass call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "tryregister":
		# username:hostname:password
		result = register(request[1], request[2], request[3])
		logging.debug("Result of tryregister call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "removeuser":
		# username:hostname:password
		result = remove_user(request[1], request[2])
		logging.debug("Result of removeuser call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "removeuser3":
		# username:hostname:password
		result = remove_user_safe(request[1], request[2], request[3])
		logging.debug("Result of removeuser3 call for %s@%s: %s" % (request[1], request[2], result))
	else:
		ejabberd.info("Unsupported method encountered: %s" % request[0])
		continue
		
	ejabberd_write(result)

logging.info("External authentication script terminating...")

#!/usr/bin/python

import sys, logging, struct, hashlib

sys.stderr = open("/var/log/ejabberd/extauth_err.log", "a")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", filename="/var/log/ejabberd/extauth.log", filemode="a")

class EjabberdInputError(Exception):
	def __init__(self, value):
		self.value = value
		
	def __str__(self):
		return repr(self.value)
		
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
	
def user_exists(username, hostname):
	if hostname not in ["envoy.local"]:
		logging.info("Invalid host specified on login (%s@%s)" % (username, hostname))
		return False
		
	if username not in ["joepie91"]:
		logging.info("Invalid username specified on login (%s@%s)" % (username, hostname))
		return False

def authenticate(username, hostname, password):
	if user_exists(username, hostname) == False:
		return False
	
	if password not in ["test"]:
		logging.info("Invalid password specified (%s@%s)" % (username, hostname))
		return False
		
	logging.debug("User %s@%s successfully authenticated." % (username, hostname))
	return True
	
logging.info("External authentication script started, waiting for ejabberd requests...")

while True:
	try:
		request = ejabberd_read()
	except EjabberdInputError, e:
		logging.warning("Exception occurred, exiting: %s" % e)
		break
	
	logging.debug("Requested operation: %s" % request[0])
	
	if request[0] == "auth":
		result = authenticate(request[1], request[2], request[3])
		logging.debug("Result of authentication call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "isuser":
		result = user_exists(request[1], request[2])
		logging.debug("Result of isuser call for %s@%s: %s" % (request[1], request[2], result))
	elif request[0] == "setpass":
		result = True
		logging.debug("Sent fake True response for setpass call.")
	else:
		ejabberd.info("Unsupported method encountered: %s" % request[0])
		continue
		
	ejabberd_write(result)

logging.info("External authentication script terminating...")

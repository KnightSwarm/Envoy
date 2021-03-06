#!/usr/bin/python

import sys, struct, subprocess

def do_request(inp):
	proc = subprocess.Popen(["python", "auth.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	hdr = struct.pack(">h", len(inp))
	proc.stdin.write(hdr)
	proc.stdin.write(inp)
	data = proc.stdout.read(4)
	rcv = struct.unpack(">hh", data)
	return repr(rcv[1] == 1)

if sys.argv[1] == "register":
	result = do_request("tryregister:testuser:envoy.local:testpass")
elif sys.argv[1] == "isuser":
	result = do_request("isuser:testuser:envoy.local")
elif sys.argv[1] == "auth":
	result = do_request("auth:testuser:envoy.local:testpass")
elif sys.argv[1] == "auth_false":
	result = do_request("auth:testuser:envoy.local:wrongpass")
elif sys.argv[1] == "auth_changed":
	result = do_request("auth:testuser:envoy.local:changedpass")
elif sys.argv[1] == "setpass":
	result = do_request("setpass:testuser:envoy.local:changedpass")
elif sys.argv[1] == "remove":
	result = do_request("removeuser:testuser:envoy.local")
elif sys.argv[1] == "removesafe":
	result = do_request("removeuser3:testuser:envoy.local:testpass")
elif sys.argv[1] == "removesafe_false":
	result = do_request("removeuser3:testuser:envoy.local:wrongpass")
else:
	sys.stderr.write("Invalid argument\n")
	exit(1)
	
print result

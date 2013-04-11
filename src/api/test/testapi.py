#!/usr/bin/env python

import requests, sys, json, random, string

conf = json.load(open("testconfig.json", "r"))

if sys.argv[1] == "register":
	user = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(12))
	passwd = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(20))
	
	response = requests.post(conf["endpoint"] + "/user/register", data={
		"username": user,
		"password": passwd,
		"fqdn": "envoy.local"
	}, headers={"Envoy-API-Id": conf["api_id"], "Envoy-API-Key": conf["api_key"]})
	
	if response.status_code == 200:
		sys.stdout.write("Successfully registered user %s@envoy.local with password %s.\n" % (user, passwd))
	else:
		sys.stderr.write("Failed to register user %s@envoy.local with password %s.\n%s\n" % (user, passwd, response.text))
elif sys.argv[1] == "lookup":
	user = sys.argv[2]
	
	response = requests.get(conf["endpoint"] + "/user/lookup", params={
		"username": user,
		"fqdn": "envoy.local"
	}, headers={"Envoy-API-Id": conf["api_id"], "Envoy-API-Key": conf["api_key"]})
	
	if response.status_code == 200:
		sys.stdout.write("Successfully looked up user %s@envoy.local.\n%s\n" % (user, response.text))
	else:
		sys.stderr.write("Failed to lookup user %s@envoy.local.\n%s\n" % (user, response.text))

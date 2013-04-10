#!/usr/bin/env python

import requests, argparse, json

parser = argparse.ArgumentParser(description="Make test requests to the Envoy API")
parser.add_argument("--post", dest="method", action="store_const", const="post", default="get", help="Make a POST request instead of a GET request.")
parser.add_argument("--raw", dest="raw", action="store_true", help="Don't parse the response.")
parser.add_argument("--param", dest="parameters", action="append", help="Specify a parameter (for POST requests).")
parser.add_argument("path", metavar="PATH", help="The API path to request.")
args = parser.parse_args()

conf = json.load(open("testconfig.json", "r"))

post_data = {}

for parameter in args.parameters:
	key, value = parameter.split("=", 1)
	post_data[key] = value

url = conf["endpoint"] + args.path

if args.method == "get":
	response = requests.get(url, params=post_data, headers={"Envoy-API-Id": conf["api_id"], "Envoy-API-Key": conf["api_key"]})
else:
	response = requests.post(url, data=post_data, headers={"Envoy-API-Id": conf["api_id"], "Envoy-API-Key": conf["api_key"]})

if response.status_code != 404:
	if args.raw == False:
		data = json.dumps(response.json(), indent=4)
	else:
		data = response.text
	print "Path: %s\tResponse code: %s\nData: %s" % (args.path, response.status_code, data)
else:
	print "Path: %s\tResponse code: 404" % args.path

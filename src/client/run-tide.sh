#!/bin/bash
cd ~/.tidesdk/sdk/linux/1.3.1-beta/ && python tidebuilder.py -n "~/projects/Envoy/src/client/Envoy Client/"

if ps aux | grep "Envoy Client" | grep -vE "grep|sass"
then
	echo "Already running, triggering reload..."
	# Very low-tech reload signal!
	touch /tmp/envoy-client-reload
else
	~/.tidesdk/sdk/linux/1.3.1-beta/Envoy\ Client/Envoy\ Client --debug
fi

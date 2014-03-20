#!/bin/bash
cd ~/.tidesdk/sdk/linux/1.3.1-beta/ && python tidebuilder.py -n -r "~/projects/Envoy/src/client/Envoy Client/"
# Somehow, TideSDK has stopped running correctly after build, so we need to run it manually...
/home/sven/.tidesdk/sdk/linux/1.3.1-beta/Envoy\ Client/Envoy\ Client/Envoy\ Client

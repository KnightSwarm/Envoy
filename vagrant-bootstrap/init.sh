#!/bin/bash

# Exit if we encounter any errors
set -e

err_report() {
	echo "=============================================="
	echo "PROBLEM ENCOUNTERED on line $1:"
	echo -n "$ "
	head -n $1 $0 | tail -n 1 # Print errored line
	echo "Exiting..."
	echo "=============================================="
}

trap 'err_report $LINENO' ERR

prosodyctl start >/dev/null
su -c "python /vagrant/src/envoyxmpp/run.py >/dev/null 2>/dev/null &" envoy

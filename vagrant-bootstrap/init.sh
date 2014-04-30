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

# We need to start the component first, to make sure that an FQDN configuration exists. Prosody will refuse to start otherwise.
/vagrant/vagrant-bootstrap/start-component.sh

# Give the component some time to generate configuration files...
sleep 10

prosodyctl start >/dev/null

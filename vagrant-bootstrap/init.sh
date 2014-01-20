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
/vagrant/vagrant-bootstrap/start-component.sh

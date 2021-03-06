#!/bin/bash

# Exit if we encounter any errors
set -e

err_report() {
	echo "==============================================" >&2
	echo "PROBLEM ENCOUNTERED on line $1:" >&2
	echo -n "$ " >&2
	head -n $1 $0 | tail -n 1 >&2 # Print errored line
	echo "Exiting..." >&2
	echo "==============================================" >&2
}

trap 'err_report $LINENO' ERR

/vagrant/vagrant-bootstrap/stop.sh

echo "Component quit, restarting..."
/vagrant/vagrant-bootstrap/start-component.sh

echo "Done!"

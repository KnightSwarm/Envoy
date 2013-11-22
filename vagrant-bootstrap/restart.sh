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

# Tell component to quit with a SIGINT...
kill -15 `pgrep -f '^python .*run_component\.py'` || true
echo "Told component to quit, waiting..."

# Wait for component to exit
until [  $(pgrep -f run_component.py | wc -l) -lt 1 ]; do
	sleep 0.5
done

echo "Component quit, restarting..."
su -c "python /vagrant/src/envoyxmpp/run_component.py &" envoy

echo "Done!"

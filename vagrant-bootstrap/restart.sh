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

# Tell component to quit with a SIGINT...
kill -15 `pgrep -f '^python .*run\.py'` || true
echo "Told component to quit, waiting..."

# Wait for component to exit
until [  $(pgrep -f run.py | wc -l) -lt 1 ]; do
	sleep 0.5
done

echo "Component quit, restarting..."
/vagrant/vagrant-bootstrap/start-component.sh

echo "Done!"

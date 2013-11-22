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

# Copy configuration
cp /vagrant/vagrant-bootstrap/template.cfg.lua /etc/prosody/prosody.cfg.lua
cp /vagrant/vagrant-bootstrap/config.json /etc/envoy/config.json >/dev/null

# Fix permissions and ownership
#-- Directory ownership
chown -R envoy:envoy /etc/envoy >/dev/null
chown -R prosody:envoy /etc/envoy/prosody >/dev/null
chown prosody:prosody /etc/prosody/prosody.cfg.lua >/dev/null
chown prosody:prosody /etc/prosody/conf.d >/dev/null
#-- Directory permissions 
chmod -R ug=rwx /etc/envoy >/dev/null
chmod -R o=rx /etc/envoy >/dev/null
#-- Hide configuration from others
chmod o-rwx /etc/prosody/prosody.cfg.lua >/dev/null

# Restart Prosody
prosodyctl restart >/dev/null

# TEMPORARY: Update SleekXMPP new_muc branch from git
cd /etc/envoy
pip install --upgrade -e 'git://github.com/fritzy/SleekXMPP.git@new_muc#egg=sleekxmpp' >/dev/null

echo "Done!"

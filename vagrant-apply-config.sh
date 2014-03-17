#!/bin/sh
# Applies a local customized configuration to the component.
vagrant ssh -c "sudo su -c 'cp /vagrant/src/config.json /etc/envoy/config.json' envoy"

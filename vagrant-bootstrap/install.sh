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

# Let's make sure we won't get bothered by errors that aren't actually errors ("unable to re-open stdin" and such)
# Source: http://serverfault.com/a/500778/117738
echo "Configuring locale..."
export LANGUAGE=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export DEBIAN_FRONTEND=noninteractive
locale-gen en_US.UTF-8 >/dev/null
dpkg-reconfigure locales >/dev/null 2>/dev/null

# Make sure we are up to date
echo "Updating packages..."
apt-get update >/dev/null
apt-get upgrade -y >/dev/null

# Get htop and such
echo "Installing tools..."
apt-get install -y htop iftop iotop git highlight multitail expect pkg-config build-essential inotify-tools > /dev/null

# Get Python and pip
echo "Installing Python..."
apt-get install -y python python-pip python-dev >/dev/null

# Get MySQL
echo "Installing MySQL..."
#-- This is to prevent it from hanging on a password prompt; the default root password will be 'vagrant'
sudo debconf-set-selections <<< 'mysql-server-5.5 mysql-server/root_password password vagrant'
sudo debconf-set-selections <<< 'mysql-server-5.5 mysql-server/root_password_again password vagrant'
apt-get install -y mysql-server mysql-client libmysql++-dev >mysql-log 2>&1

# Get lighttpd and PHP (with memcached)
echo "Installing lighttpd and PHP..."
apt-get install -y lighttpd php5-cgi memcached php5-memcache php5-mysql php5-curl php5-dev php-pear libzmq1 libzmq-dev >/dev/null 2>&1
expect -f /vagrant/vagrant-bootstrap/zmq-beta.exp >/dev/null # This installs the ZMQ PHP plugin through PECL, auto-answering interactive prompts
echo "extension=zmq.so" > /etc/php5/conf.d/20-zmq.ini
chmod o+r /etc/php5/conf.d/20-zmq.ini

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt -q >&2

# Install optional libraries for URL preview resolving etc.
echo "Installing optional Python modules..."
pip install -r optional_deps.txt -q >&2

# Set up Prosody repository
echo "Setting up Prosody repository..."
DIST="$(lsb_release -sc)"
echo "deb http://packages.prosody.im/debian $DIST main" > /etc/apt/sources.list.d/prosody.list
wget https://prosody.im/files/prosody-debian-packages.key -O- 2>/dev/null | sudo apt-key add - >/dev/null
apt-get update >/dev/null

# Install Prosody
echo "Installing Prosody and dependencies..."
apt-get install -y prosody luarocks >/dev/null
luarocks install lpc >/dev/null

# We don't want Prosody to start automatically, so let's get rid of it again
pkill -f '^[^ ]*lua5\.1.*bin/prosody'

# Set up the Envoy user
echo "Setting up users and groups..."
adduser --system --group --disabled-password --shell "/bin/bash" --home "/home/envoy" envoy >/dev/null

# Add the Prosody user to the Envoy group
usermod -a -G envoy prosody >/dev/null

# Create directory structures
mkdir -p /etc/envoy/prosody >/dev/null
mkdir -p /etc/envoy/extauth >/dev/null
mkdir -p /etc/envoy/certs >/dev/null
mkdir /etc/prosody/conf.d >/dev/null 2>/dev/null || true

# Copy configuration
echo "Configuring..."
cp mysql-public.cnf /etc/mysql/conf.d/public.cnf >/dev/null
cp template.cfg.lua /etc/prosody/prosody.cfg.lua
ln -s /vagrant/vagrant-bootstrap/prosody-modules /etc/envoy/prosody/modules >/dev/null
ln -s /vagrant/src/auth/auth.py /etc/envoy/extauth/auth.py >/dev/null
cp /vagrant/vagrant-bootstrap/config.json /etc/envoy/config.json >/dev/null
touch /etc/envoy/extauth/extauth.log >/dev/null
touch /etc/envoy/extauth/extauth_err.log >/dev/null
tar -xzf certs.tar.gz -C /etc/envoy/certs >/dev/null
ln -s /vagrant/src/envoyxmpp /usr/lib/python2.7/envoyxmpp

mkdir /etc/lighttpd/vhosts.d/
cp /vagrant/vagrant-bootstrap/lighttpd.conf /etc/lighttpd/lighttpd.conf
cp /vagrant/vagrant-bootstrap/api.envoy.local.conf /etc/lighttpd/vhosts.d/
cp /vagrant/vagrant-bootstrap/panel.envoy.local.conf /etc/lighttpd/vhosts.d/
cp /vagrant/vagrant-bootstrap/php.ini /etc/php5/cgi/php.ini

# TEMPORARY: Pre-create envoy.local Prosody data directory, so that Envoy can access it.
mkdir "/var/lib/prosody/envoy%2elocal"

# Restart MySQL to apply public binding changes
/etc/init.d/mysql restart >/dev/null

# Restart lighttpd to apply vhost changes
/etc/init.d/lighttpd restart >/dev/null

# Fix permissions and ownership
echo "Setting ownership and permissions..."
#-- Directory ownership
chown -R envoy:envoy /etc/envoy >/dev/null
chown -R prosody:envoy /etc/envoy/prosody >/dev/null
chown prosody:prosody /etc/prosody/prosody.cfg.lua >/dev/null
chown prosody:prosody /etc/prosody/conf.d >/dev/null
chown -R prosody:envoy /var/lib/prosody
#-- Directory permissions 
chmod -R ug=rwx /etc/envoy >/dev/null
chmod -R ug=rwx /var/lib/prosody >/dev/null
chmod -R o=rx /etc/envoy >/dev/null
#-- Hide configuration from others
chmod o-rwx /etc/prosody/prosody.cfg.lua >/dev/null
#-- Add the httpd user to the envoy group
usermod -a -G envoy www-data

# Set /etc/hosts
echo "Configuring /etc/hosts..."
echo "127.0.0.1 envoy.local" >> /etc/hosts
echo "127.0.0.1 api.envoy.local" >> /etc/hosts
echo "127.0.0.1 panel.envoy.local" >> /etc/hosts

# Create database, import database dump
echo "Setting up database..."
mysql --user=root --password=vagrant -D mysql < root-public.sql
mysql --user=root --password=vagrant -e "CREATE DATABASE envoy;"
mysql --user=root --password=vagrant -D envoy < structure.sql
mysql --user=root --password=vagrant -D envoy < data.sql

# TEMPORARY: Install SleekXMPP new_muc branch from git
echo "Installing SleekXMPP new_muc..."
cd /etc/envoy
pip install -e 'git://github.com/fritzy/SleekXMPP.git@new_muc#egg=sleekxmpp' >/dev/null

# Symlink template path
ln -s /vagrant/src/envoyxmpp/templates /etc/envoy/src/templates

echo "Starting services..."
/vagrant/vagrant-bootstrap/init.sh

echo "Done!"

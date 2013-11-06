#!/usr/bin/env python

import subprocess, os, sys
import setuplib

stfu = open("/dev/null", "w")

package_list_64 = [
	"liblua5.1-sec0_0.3.2-2prosody1_amd64.deb",
	"prosody_0.8.2-1_amd64.deb"
]

proc = subprocess.Popen(["dpkg", "--print-architecture"], stdout=subprocess.PIPE)
(stdout, _) = proc.communicate()
architecture = stdout.strip()

if architecture not in ["x86_64", "amd64"]:
	sys.stderr.write("This installer only works on x86_64 architectures. If you believe\n")
	sys.stderr.write("this is in error, please file a bug report with the output of uname -m.\n")
	exit(1)

# This Vagrant installer really only needs to support 64-bits
package_list = package_list_64

sys.stdout.write("Installing packages...\n")

for package in package_list:
	result = subprocess.call(["dpkg", "--unpack", package], stdout=stfu, stderr=stfu)
	
	if result != 0:
		sys.stderr.write("An error occurred while installing %s. Exiting...\n" % package)
		exit(result)
		
	sys.stdout.write("Installed %s.\n" % package)

sys.stdout.write("Installing dependencies...\n")

result = subprocess.call(["apt-get", "install", "-f", "-y"], stdout=stfu, stderr=stfu)

if result != 0:
	sys.stderr.write("Failed to install dependencies. Exiting...\n")
	exit(result)
	
sys.stdout.write("Dependencies installed.\n")

# We'll need to find the prosody user to set the correct permissions and ownership.

passwd = open("/etc/passwd", "r")
uid = int([x for x in passwd.readlines() if "prosody" in x][0].split(":")[2])
passwd.close()

group = open("/etc/group", "r")
gid = int([x for x in group.readlines() if "prosody" in x][0].split(":")[2])
group.close()

setuplib.create_directory("/etc/envoy", False, uid, gid, "u+rwx g+rwx o+rx")
setuplib.create_directory("/etc/envoy/prosody", False, uid, gid, "u+rwx g+rwx o+rx")

envoy_uid, envoy_gid = setuplib.add_user("envoy", extra_group_users=["prosody"])
prosody_uid, prosody_gid = (uid, gid)

sys.stdout.write("Directory structures created.\n")

setuplib.copy_file("template.cfg.lua", "/etc/prosody/prosody.cfg.lua", True, prosody_uid, envoy_gid, "u+rwx g+rwx")

sys.stdout.write("Configuration template copied.\n")

setuplib.copy_directory("prosody-modules", "/etc/envoy/prosody/modules", True, prosody_uid, prosody_gid, "u+rwx g+rx o+rx")

#!/usr/bin/env python

import subprocess, os, sys
import setuplib

stfu = open("/dev/null", "w")

package_list_64 = [
	"liblua5.1-sec0_0.3.2-2prosody1_amd64.deb",
	"prosody_0.8.2-1_amd64.deb"
]

package_list_32 = [
	"liblua5.1-sec0_0.3.2-2prosody1_i386.deb",
	"prosody_0.8.2-1_i386.deb"
]

proc = subprocess.Popen(["dpkg", "--print-architecture"], stdout=subprocess.PIPE)
(stdout, _) = proc.communicate()
architecture = stdout.strip()

if architecture not in ["i386", "i686", "x86_64", "amd64"]:
	sys.stderr.write("This installer only works on i386/i686/x86_64 architectures. If you believe\n")
	sys.stderr.write("this is in error, please file a bug report with the output of uname -m.\n")
	exit(1)

if architecture in ["i386", "i686"]:
	package_list = package_list_32
elif architecture in ["x86_64", "amd64"]:
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

sys.stdout.write("Directory structures created.\n")

setuplib.copy_file("template.cfg.lua", "/etc/prosody/prosody.cfg.lua", True, uid, gid, "u+rwx g+rwx")

sys.stdout.write("Configuration template copied.\n")

setuplib.copy_directory("prosody-modules", "/etc/envoy/prosody-modules", True, uid, gid, "u+rwx g+rx o+rx")

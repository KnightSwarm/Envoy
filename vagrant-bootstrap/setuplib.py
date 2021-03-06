# Generic setup library for Python-based installation scripts.
# Written by Sven Slootweg <admin@cryto.net>.
# Licensed under the WTFPL.

import stat, os, shutil, urllib, subprocess
from itertools import dropwhile

def create_directory(path, ignore_failure=True, uid=-1, gid=-1, modes=""):
	try:
		os.makedirs(path)
	except OSError, e:
		if ignore_failure:
			pass
		else:
			raise

	if uid != -1 or gid != -1:
		os.chown(path, uid, gid)
	
	if modes != "":
		set_modes(path, modes)

def copy_file(source, destination, ignore_failure=True, uid=-1, gid=-1, modes=""):
	if ignore_failure == False:
		if os.path_exists(destination):
			raise Exception("Destination path already exists.")
	
	try:
		shutil.copy(source, destination)
	except IOError, e:
		if ignore_failure:
			pass
		else:
			raise
	
	if uid != -1 or gid != -1:
		os.chown(destination, uid, gid)
	
	if modes != "":
		set_modes(destination, modes)
		
def copy_directory(source, destination, ignore_failure=True, uid=-1, gid=-1, modes=""):
	if ignore_failure == False:
		if os.path_exists(destination):
			raise Exception("Destination path already exists.")
			
	try:
		shutil.copytree(source, destination)
	except IOError, e:
		if ignore_failure:
			pass
		else:
			raise
	
	if uid != -1 or gid != -1:
		os.chown(destination, uid, gid)
		
		for root, dirs, files in os.walk(destination):
			for item in dirs:
				os.chown(os.path.join(root, item), uid, gid)
			for item in files:
				os.chown(os.path.join(root, item), uid, gid)
				
	if modes != "":
		set_modes(destination, modes)
		
		for root, dirs, files in os.walk(destination):
			for item in dirs:
				set_modes(os.path.join(root, item), modes)
			for item in files:
				set_modes(os.path.join(root, item), modes)

def create_file(path, contents="", uid=-1, gid=-1, modes=""):
	f = open(path, "w")
	
	if contents != "":
		f.write(contents)
		
	f.close()
	
	if uid != -1 or gid != -1:
		os.chown(path, uid, gid)
	
	if modes != "":
		set_modes(path, modes)

def set_modes(path, modes):
	mode_map = {
		"u": {
			"r": stat.S_IRUSR,
			"w": stat.S_IWUSR,
			"x": stat.S_IXUSR
		},
		"g": {
			"r": stat.S_IRGRP,
			"w": stat.S_IWGRP,
			"x": stat.S_IXGRP
		},
		"o": {
			"r": stat.S_IROTH,
			"w": stat.S_IWOTH,
			"x": stat.S_IXOTH
		}
		
	}
	
	chunks = modes.split(" ")
	mode = 0
	
	for chunk in chunks:
		usertype, changes = chunk.split("+")
		
		if usertype in mode_map:
			for change in list(changes):
				if change in mode_map[usertype]:
					mode = mode | mode_map[usertype][change]
				else:
					raise Exception("Unknown permission in modes specification.")
		elif usertype == "a":
			for change in list(changes):
				for i in mode_map:
					if change in mode_map[i]:
						mode = mode | mode_map[i][change]
		else:
			raise Exception("Unknown user type in modes specification.")
		
	os.chmod(path, mode)

def download_file(name, mirrors):
	try:
		file_mirrors = mirrors[name]
	except KeyError, e:
		raise Exception("No such file exists in the mirror list.")
	
	for url in file_mirrors:
		try:
			urllib.urlretrieve(url, name)
		except:
			continue
		else:
			return name
	
	raise Exception("No functional mirrors found for this file.")

def install_rpm(path):
	stfu = open("/dev/null", "wb")
	
	result = subprocess.call(["yum", "--nogpgcheck", "install", "-y", path], stdout=stfu, stderr=stfu)
	
	stfu.close()
	
	if result != 0:
		raise Exception("Failed to install package.")

def install_remote_rpm(name, mirrors):
	download_file(name, mirrors)
	install_rpm(name)
	
def add_user(new_username, group=True, extra_group_users=[]):
	open("/etc/passwd.lock", "w").close()
	open("/etc/group.lock", "w").close()
	
	# Find highest non-reserved UID in the user list
	passwd = open("/etc/passwd", "r+")
	highest_uid = 1000

	for line in passwd:
		username, password, uid, gid, name, homedir, shell = line.split(":")
		
		if username == new_username:
			raise Exception("User already exists")
		
		if int(uid) < 32000 and int(uid) > highest_uid:
			highest_uid = int(uid)
			
	new_uid = highest_uid + 1
	
	if group == True:
		# Find highest non-reserved GID in the user list
		grp = open("/etc/group", "r+")
		highest_gid = 1000

		for line in grp:
			groupname, password, gid, users = line.split(":")
			
			if groupname == new_username:
				raise Exception("Group already exists")
			
			if int(gid) < 32000 and int(gid) > highest_gid:
				highest_gid = int(gid)
				
		new_gid = highest_gid + 1
		grp.seek(0, 2)
		grp.write("%s::%d:%s\n" % (new_username, new_gid, ",".join(extra_group_users)))
		grp.close()
	else:
		new_gid = -1
		
	create_directory("/home/%s" % new_username, True, new_uid, new_gid, "u+rwx g+rx")
	
	passwd.seek(0, 2)
	passwd.write("%s::%d:%d::/home/%s:/bin/bash\n" % (new_username, new_uid, new_gid, new_username))
	passwd.close()
	
	os.remove("/etc/passwd.lock")
	os.remove("/etc/group.lock")
	
	return (new_uid, new_gid)

def rindex(lst, item):
	# http://stackoverflow.com/a/6892096/1332715
	try:
		return dropwhile(lambda x: lst[x].strip() != item, reversed(xrange(len(lst)))).next()
	except StopIteration:
		raise ValueError, "rindex(lst, item): item not in list"

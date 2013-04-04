import passlib.hash, passlib.utils, base64, os

def pbkdf2_sha512(password, salt="", iterations=30000):
	# passlib returns a modular-crypt-formatted hash, and that's not
	# what we want. This function will decode the hash and turn it
	# into a tuple that uses standard base64 to encode data.
	if salt == "":
		crypt = passlib.hash.pbkdf2_sha256.encrypt(password, salt_size=24, rounds=iterations)
	else:
		crypt = passlib.hash.pbkdf2_sha256.encrypt(password, salt=salt, rounds=iterations)
	
	_, _, rounds, salt_ab64, digest_ab64 = crypt.split("$")
	salt = base64.b64encode(passlib.utils.ab64_decode(salt_ab64))
	digest = base64.b64encode(passlib.utils.ab64_decode(digest_ab64))
	
	return (digest, salt, rounds)

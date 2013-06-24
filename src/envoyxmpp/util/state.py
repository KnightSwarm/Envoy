AVAILABLE = 1
AWAY = 2
XA = 3
DND = 4
CHAT = 5
UNAVAILABLE = 6
UNKNOWN = 7

def from_string(string):
	table = {
		"available": AVAILABLE,
		"away": AWAY,
		"xa": XA,
		"dnd": DND,
		"chat": CHAT,
		"unavailable": UNAVAILABLE
	}
	
	try:
		return table[string]
	except KeyError, e:
		raise ValueException("No such presence exists.")
		

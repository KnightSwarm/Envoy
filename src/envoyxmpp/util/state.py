AVAILABLE = 1
AWAY = 2
XA = 3
DND = 4
CHAT = 5
UNAVAILABLE = 6
UNKNOWN = 7

table = {
	"available": AVAILABLE,
	"away": AWAY,
	"xa": XA,
	"dnd": DND,
	"chat": CHAT,
	"unavailable": UNAVAILABLE,
	"unknown": UNKNOWN
}

def from_string(string):
	try:
		return table[string]
	except KeyError, e:
		raise ValueException("No such presence exists.")
		
def from_state(state):
	try:
		return [key for key, val in table.iteritems() if val == state][0]
	except IndexError, e:
		raise ValueException("No such state exists.")

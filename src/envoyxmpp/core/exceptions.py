class NotFoundException(Exception):
	pass
	
class ConfigurationException(Exception):
	pass

class LibraryUnavailableException(Exception):
	# This exception is intended for use when an optional library is not installed or
	# is unavailable, and its unavailability makes it impossible to fulfill the request.
	# An example is its use in URL preview resolvers.
	pass

class ResolutionFailedException(Exception):
	# Raised when a URL preview resolver failed; eg. if the URL doesn't exist, or
	# the API key doesn't have access to the resource.
	pass
	

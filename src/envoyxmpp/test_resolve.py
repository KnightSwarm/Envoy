import sys

from core.handlers import ResolveHandler
from core.providers import ConfigurationProvider

# Initialize configuration
configuration = ConfigurationProvider.Instance("test")
configuration.read("../config.json")

handler = ResolveHandler.Instance("test")

print handler.resolve(sys.argv[1], "")

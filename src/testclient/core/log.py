import logging

def info(message):
	logging.info("[application] %s" % message)
	
def debug(message):
	logging.debug("[application] %s" % message)
	
def warning(message):
	logging.warning("[application] %s" % message)
	
def error(message):
	logging.error("[application] %s" % message)
	
def critical(message):
	logging.critical("[application] %s" % message)

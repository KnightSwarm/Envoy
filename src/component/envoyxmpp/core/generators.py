from .util import LocalSingleton, LocalSingletonBase

import subprocess, os, stat

@LocalSingleton
class FqdnConfigurationGenerator(LocalSingletonBase):
	def generate(self, fqdn):
		fqdn_provider = FqdnProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		configuration = ConfigurationProvider.Instance(self.identifier)
		
		fqdn = fqdn_provider.normalize_fqdn(fqdn)
		
		with open(os.path.join(configuration.asset_path, "templates/vhost.cfg.lua"), "r") as template_file:
			template = template_file.read()
			
		config = template.replace("$FQDN", fqdn.fqdn).replace("$PRIMARY_FQDN", component.get_fqdn().fqdn)
		
		with open("/etc/envoy/hosts/%s.cfg.lua" % fqdn.fqdn, "w") as config_file:
			config_file.write(config)
			
		os.chmod("/etc/envoy/hosts/%s.cfg.lua" % fqdn.fqdn, stat.S_IRWXU | stat.S_IRWXG)
			
		if not os.path.exists("/etc/envoy/certs/%s.cert" % fqdn.fqdn):
			subprocess.call(["openssl", "req", "-new", "-newkey", "rsa:4096", "-days", "365", "-nodes", "-x509", "-subj", "/CN=%s" % fqdn.fqdn, "-keyout", "/etc/envoy/certs/%s.key" % fqdn.fqdn, "-out", "/etc/envoy/certs/%s.cert" % fqdn.fqdn])
				
			os.chmod("/etc/envoy/certs/%s.key" % fqdn.fqdn, stat.S_IRWXU | stat.S_IRWXG)
			os.chmod("/etc/envoy/certs/%s.cert" % fqdn.fqdn, stat.S_IRWXU | stat.S_IRWXG)
		
from .providers import FqdnProvider, ConfigurationProvider
from .component import Component

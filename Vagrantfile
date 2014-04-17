# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "debian72-64"
  config.vm.box_url = "http://cryto.net/~joepie91/debian72-64.box"

  config.vm.define "default", primary: true do |default|
    default.vm.network :forwarded_port, guest: 5222, host: 5222
    default.vm.network :forwarded_port, guest: 3306, host: 3307
    default.vm.network :forwarded_port, guest: 80, host: 8080
    default.vm.synced_folder "../cphp", "/usr/share/php/cphp"
    default.vm.provision :shell, :path => "vagrant-bootstrap/bootstrap.sh"
  end
  
  config.vm.define "testing" do |testing|
    testing.vm.network :forwarded_port, guest: 5222, host: 5223
  end
end

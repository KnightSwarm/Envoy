while true; do
	mkdir /vagrant/dev-logs
	inotifywait -e modify /etc/envoy/envoy.log /etc/envoy/panel.log /var/log/lighttpd/error.log && rsync -avz /etc/envoy/*.log /vagrant/dev-logs/ && rsync -avz /var/log/lighttpd/error.log /vagrant/dev-logs/
done

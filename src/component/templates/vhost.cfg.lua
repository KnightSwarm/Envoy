-- Virtual hosts
VirtualHost "$FQDN"
        enabled = true
        
        admins = { "component.$PRIMARY_FQDN" }

        -- Assign this host a certificate for TLS, otherwise it would use the one
        -- set in the global section (if any).
        -- Note that old-style SSL on port 5223 only supports one certificate, and will always
        -- use the global one.
        ssl = {
                key = "/etc/envoy/certs/$FQDN.key";
                certificate = "/etc/envoy/certs/$FQDN.cert";
        }

-- The standard MUC component
Component "conference.$FQDN" "muc"
	name = "Rooms for $FQDN"
	restrict_room_creation = true
        admins = { "component.$PRIMARY_FQDN" }

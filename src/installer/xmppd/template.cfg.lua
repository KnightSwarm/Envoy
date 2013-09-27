--------- Template configuration file for Prosody as a part of Envoy -----------

-- We have additional plugins installed.
plugin_paths = { "/etc/envoy/prosody/modules" }

-- The pidfile keeps track of the running Prosody process.
pidfile = "/etc/envoy/prosody/prosody.pid"

modules_enabled = {
                "roster"; -- Allow users to have a roster. Recommended ;)
                "saslauth"; -- Authentication for clients and servers. Recommended if you want to log in.
                "tls"; -- Add support for secure TLS on c2s/s2s connections
                "dialback"; -- s2s dialback support
                "disco"; -- Service discovery
                "private"; -- Private XML storage (for room bookmarks, etc.)
                "vcard"; -- Allow users to set vCards
                "privacy"; -- Support privacy lists
                "legacyauth"; -- Legacy authentication. Only used by some old clients and bots.
                "version"; -- Replies to server version requests
                "uptime"; -- Report how long server has been running
                "time"; -- Let others know the time here on this server
                "ping"; -- Replies to XMPP pings with pongs
                "pep"; -- Enables users to publish their mood, activity, playing music and more
                "register"; -- Allow users to register on this server using a client and change passwords
                "adhoc"; -- Support for "ad-hoc commands" that can be executed with an XMPP client
                "admin_adhoc"; -- Allows administration via an XMPP client that supports ad-hoc commands
                "posix"; -- POSIX functionality, sends server to background, enables syslog, etc.
                "groups"; -- Shared roster support
                "announce"; -- Send announcement to all online users
                "watchregistrations"; -- Alert admins of registrations
                "auth_external"; -- Handles user authentication via an ejabberd extauth script.
                "forward"; -- Forwards all stanzas to an external component and relays responses.
};

-- For now, we will only allow registration through the API.
allow_registration = false;

-- These are the default SSL settings for the Prosody instance.
ssl = {
        key = "/etc/envoy/certs/localhost.key";
        certificate = "/etc/envoy/certs/localhost.cert";
}

-- Disallow plaintext connetions.
c2s_require_encryption = true
s2s_require_encryption = true

-- We will use an external ejabberd-style authentication script.
authentication = "external"
external_auth_protocol = "ejabberd"
external_auth_command = "/etc/envoy/extauth/auth.py"

-- System logging
log = {
        info = "/etc/envoy/prosody/prosody.log";  -- TODO: Let installer pick between 'info' or 'debug' log level.
        error = "/etc/envoy/prosody/prosody.err";
}

-- Virtual hosts
VirtualHost "envoy.local"
        enabled = true -- Remove this line to enable this host

        -- Assign this host a certificate for TLS, otherwise it would use the one
        -- set in the global section (if any).
        -- Note that old-style SSL on port 5223 only supports one certificate, and will always
        -- use the global one.
        ssl = {
                key = "/etc/envoy/certs/envoy.local.key";
                certificate = "/etc/envoy/certs/envoy.local.crt";
        }

-- The external Envoy component
Component "component.envoy.local"
        component_secret = "password"  -- TODO: Make installer generate a password for this.

-- We will also include everything in conf.d - these files will hold host-specific configuration.
Include "conf.d/*.lua"

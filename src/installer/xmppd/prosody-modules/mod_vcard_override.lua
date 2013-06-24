local datamanager = require "util.datamanager";
local usermanager = require "core.usermanager";
local st = require "util.stanza";
local host = module.host;
local jid_split = require "util.jid".split;

module:hook("iq/bare/vcard-temp:vCard", function(event)
	local session, stanza = event.origin, event.stanza;
	local to = stanza.attr.to;
	local username = jid_split(to);
	if not username then return end

	local default_vcard = datamanager.load(username, host, "default_vcard");
	local exists = usermanager.user_exists(username, host);
	module:log("debug", "has %s: %s", "default_vcard", tostring(default_vcard));
	module:log("debug", "has %s: %s", "exists", tostring(exists));

	if default_vcard and exists then
		module:log("debug", "sending stanza: %s", tostring(default_vcard))
		session.send(st.iq({ type = "result", to = stanza.attr.from, from = stanza.attr.to, id = stanza.attr.id }):text(default_vcard));
		-- session.send(default_vcard);
		return true;
	end
end, 1);

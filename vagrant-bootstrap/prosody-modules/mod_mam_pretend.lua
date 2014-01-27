-- Pretend-XEP-0313 module
--
-- Code from original mod_mam.lua (C) 2011-2012 Kim Alvefur
-- Modifications (C) 2014 Sven Slootweg
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local xmlns_mam = "urn:xmpp:mam:tmp";
local uuid = require "util.uuid";

-- Handle messages
local function message_handler(event)
	local origin, stanza = event.origin, event.stanza;
	local stanza_type = stanza.attr.type or "normal";

	-- We don't store messages of these types
	if stanza_type == "error" or stanza_type == "headline" then
		module:log("debug", "Not archiving stanza: %s (content)", stanza:top_tag());
		return;
	end
	
	id = uuid.generate();
	stanza:tag("archived", { xmlns = xmlns_mam, by = "component.envoy.local", id = id }):up();
	module:log("debug", "Archiving stanza: %s (content)", stanza:top_tag());
end

-- Only stanzas sent by local clients
module:hook("pre-message/bare", message_handler, 2);
module:hook("pre-message/full", message_handler, 2);

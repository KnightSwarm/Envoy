--[[
  Prosody mod_forward (MIT)
  Copyright (c) 2013 Waqas Hussain
  Copyright (C) 2013 Matthew Wild
   
  Permission is hereby granted, free of charge, to any person obtaining 
  a copy of this software and associated documentation files (the 
  "Software"), to deal in the Software without restriction, including 
  without limitation the rights to use, copy, modify, merge, publish, 
  distribute, sublicense, and/or sell copies of the Software, and to 
  permit persons to whom the Software is furnished to do so, subject to 
  the following conditions:
   
  The above copyright notice and this permission notice shall be 
  included in all copies or substantial portions of the Software.
   
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY 
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
--]]


local component_jid = module:get_option_string("forward_component", "component.envoy.local");
local block_original = module:get_option_boolean("forward_and_drop", false) or nil; -- Whether to drop the original stanza

local prosody = prosody;
local core_post_stanza = prosody.core_post_stanza or core_post_stanza;
local st = require "util.stanza";

local xmlns_forward = "urn:xmpp:forward:0";

function handle_stanza(event)
	local stanza = event.stanza;

	if stanza.attr.from == component_jid then
    return;
  end
  stanza = st.clone(stanza);
  stanza.attr.xmlns = "jabber:client";
	local message = st.message({ to=component_jid, from=module.host })
    :tag("forwarded", { xmlns = xmlns_forward })
      :add_child(stanza);

	module:log("debug", "got from user: %s", tostring(stanza));
	module:log("debug", "sending to component: %s", tostring(message));

	core_post_stanza(hosts[module.host], message);
	return block_original;
end

function handle_from_component(event)
  local origin, stanza = event.origin, event.stanza;
  if origin.host ~= component_jid then
    module:log("debug", "Ignoring stanza from %s", origin.host);
    return;
  elseif origin == hosts[module.host] then
    return; -- Ignore a stanza we sent
  end
  local forwarded = stanza:get_child("forwarded", xmlns_forward);
  if not forwarded or #forwarded.tags ~= 1 then
    module:log("warn", "Received a stanza from %s without anything to forward", component_jid);
    return;
  end
  module:log("debug", "Received stanza from %s, sending...", component_jid)
  core_post_stanza(hosts[module.host], forwarded.tags[1]);
  return true;
end

-- Hook all stanzas from clients
module:hook("pre-iq/bare", handle_stanza, 1);
module:hook("pre-message/bare", handle_stanza, 1);
module:hook("pre-presence/bare", handle_stanza, 1);
module:hook("pre-iq/full", handle_stanza, 1);
module:hook("pre-message/full", handle_stanza, 1);
module:hook("pre-presence/full", handle_stanza, 1);
module:hook("pre-iq/host", handle_stanza, 1);
module:hook("pre-message/host", handle_stanza, 1);
module:hook("pre-presence/host", handle_stanza, 1);
module:hook("presence/full", handle_stanza, 1);

-- Hook stanzas coming to the host we're loaded on
-- (these might be from our component)
module:hook("message/host", handle_from_component);

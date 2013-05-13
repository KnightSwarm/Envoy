--
-- NOTE: currently this uses lpc; when waqas fixes process, it can go back to that
--
-- Prosody IM
-- Copyright (C) 2010 Waqas Hussain
-- Copyright (C) 2010 Jeff Mitchell
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--


local nodeprep = require "util.encodings".stringprep.nodeprep;
--local process = require "process";
local lpc = require "lpc";

local config = require "core.configmanager";
local log = module._log;
local host = module.host;
local script_type = config.get(host, "core", "external_auth_protocol") or "generic";
assert(script_type == "ejabberd" or script_type == "generic");
local command = config.get(host, "core", "external_auth_command") or "";
assert(type(command) == "string");
assert(not host:find(":"));
local usermanager = require "core.usermanager";
local jid_bare = require "util.jid".bare;
local new_sasl = require "util.sasl".new;

--local proc;
local pid;
local readfile;
local writefile;

local function send_query(text)
	if pid and lpc.wait(pid,1) ~= nil then
    	    log("debug","error, process died, force reopen");
	    pid=nil;
	end
	if not pid then
		log("debug", "Opening process " .. command);
		-- proc = process.popen(command);
		pid, writefile, readfile = lpc.run(command);
	end
	-- if not proc then
	if not pid then
		log("debug", "Process failed to open");
		return nil;
	end
	-- proc:write(text);
	-- proc:flush();

	writefile:write(text);
	writefile:flush();
	if script_type == "ejabberd" then
		-- return proc:read(4); -- FIXME do properly
		return readfile:read(4); -- FIXME do properly
	elseif script_type == "generic" then
		-- return proc:read(1);
		return readfile:read();
	end
end

function do_query(kind, username, password)
	if not username then return nil, "not-acceptable"; end
	username = nodeprep(username);
	if not username then return nil, "jid-malformed"; end
	
	local query = (password and "%s:%s:%s:%s" or "%s:%s:%s"):format(kind, username, host, password);
	local len = #query
	if len > 1000 then return nil, "policy-violation"; end
	
	if script_type == "ejabberd" then
		local lo = len % 256;
		local hi = (len - lo) / 256;
		query = string.char(hi, lo)..query;
	end
	if script_type == "generic" then
		query = query..'\n';
	end
	
	local response = send_query(query);
	if (script_type == "ejabberd" and response == "\0\2\0\0") or
		(script_type == "generic" and response == "0") then
			return nil, "not-authorized";
	elseif (script_type == "ejabberd" and response == "\0\2\0\1") or
		(script_type == "generic" and response == "1") then
			return true;
	else
		log("debug", "Nonsense back");
		--proc:close();
		--proc = nil;
		return nil, "internal-server-error";
	end
end

function new_external_provider(host)
	local provider = { name = "external" };

	function provider.test_password(username, password)
		return do_query("auth", username, password);
	end

	function provider.set_password(username, password)
		return do_query("setpass", username, password);
	end

	function provider.user_exists(username)
		return do_query("isuser", username);
	end

	function provider.create_user(username, password) return nil, "Account creation/modification not available."; end
	
	function provider.get_sasl_handler()
		local testpass_authentication_profile = {
			plain_test = function(sasl, username, password, realm)
				local prepped_username = nodeprep(username);
				if not prepped_username then
					log("debug", "NODEprep failed on username: %s", username);
					return "", nil;
				end
				return usermanager.test_password(prepped_username, realm, password), true;
			end,
		};
		return new_sasl(module.host, testpass_authentication_profile);
	end

	function provider.is_admin(jid)
		local admins = config.get(host, "core", "admins");
		if admins ~= config.get("*", "core", "admins") then
			if type(admins) == "table" then
				jid = jid_bare(jid);
				for _,admin in ipairs(admins) do
					if admin == jid then return true; end
				end
			elseif admins then
				log("error", "Option 'admins' for host '%s' is not a table", host);
			end
		end
		return usermanager.is_admin(jid); -- Test whether it's a global admin instead
	end

	return provider;
end

module:add_item("auth-provider", new_external_provider(module.host));

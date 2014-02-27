<?php
/* Copyright 2013 by Sven Slootweg <admin@cryto.net>
 * 
 * This file is part of Envoy.
 * 
 * Envoy is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * Envoy is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with Envoy.  If not, see <http://www.gnu.org/licenses/>. */

if(!isset($_APP)) { die("Unauthorized."); }

$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

function autoload_class($class_name) 
{
	global $_APP;
	
	$class_name = str_replace("\\", "/", strtolower($class_name));
	
	if(file_exists("classes/{$class_name}.php"))
	{
		require_once("classes/{$class_name}.php");
	}
}

spl_autoload_register('autoload_class');

/* Load the Envoy PHP API library... */
require("lib/envoylib/base.php");

/* If the user is logged in, we use their keypair (stored in the session data).
 * If not, we use the master keypair, since the only call that can be made
 * is an authentication and keypair retrieval call. */
if(!empty($_SESSION["user_id"]))
{
	/* User keypair */
	$sAPI = new EnvoyLib\API($cphp_config->api->endpoint, $_SESSION["api_id"], $_SESSION["api_key"]);
}
else
{
	/* Master keypair */
	$sAPI = new EnvoyLib\API($cphp_config->api->endpoint, $cphp_config->api->id, $cphp_config->api->key);
}

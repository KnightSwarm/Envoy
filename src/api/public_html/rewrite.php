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

$_APP = true;

$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

$_CPHP_REST = true;
require("cphp-rest/base.php");

require("lib/pbkdf2.php");

use \CPHP\REST;

$API = new \CPHP\REST\APIServer();
$API->LoadConfiguration("../../api.json"); 

$API->RegisterDecoder("room", "jid", function($api, $value, $filters){
	if(!preg_match("/([^@]+)@conference\.(.+)/", $value, $matches))
	{
		throw new CPHP\REST\BadDataException("Specified room JID is not a valid JID.");
	}
	
	list($roomname, $fqdn) = $matches;
	$fqdn = $api->Fqdn($fqdn);
	return array("fqdn" => $fqdn->id, "roomname" => $roomname);
});

$API->RegisterEncoder("room", "jid", function($api, $resource){
	return "{$resource->roomname}@conference.{$resource->fqdn->fqdn}";
});

$API->RegisterDecoder("user", "jid", function($api, $value, $filters){
	if(strpos($value, "@") === false)
	{
		/* Did not contain an @. */
		throw new \CPHP\REST\BadDataException("The specified username is not a valid XMPP address.");
	}
	
	list($username, $fqdn) = explode("@", $value, 2);
	$fqdn = $api->Fqdn($fqdn);
	return array("fqdn" => $fqdn->id, "username" => $username);
});

$API->RegisterEncoder("user", "jid", function($api, $resource){
	return "{$resource->username}@{$resource->fqdn_string}";
});

$API->RegisterEncoder("user", "full_name", function($api, $resource){
	return "{$resource->first_name} {$resource->last_name}";
});

$API->RegisterEncoder("api_key", "access_level", function($api, $resource){
	try
	{
		/* Find service-wide permissions, if any. */
		$permissions = $resource->ListPermissions(array("fqdn" => 0), true);
	}
	catch (CPHP\REST\NotFoundException $e)
	{
		/* No service-wide permissions. */
		$permissions = array();
	}
	
	/* Master (server-only) access. */
	foreach($permissions as $permission)
	{
		if($permission->access_level == 200 && $resource->type == "server")
		{
			return 200;
		}
	}
	
	/* Service-administrative access. */
	foreach($permissions as $permission)
	{
		if($permission->access_level == 150 && $resource->user->access_level >= 150)
		{
			return 150;
		}
	}
	
	$fqdn = $resource->user->fqdn;
	
	/* FQDN-specific access. */
	try
	{
		$fqdn_permissions = $resource->ListPermissions(array("fqdn" => $fqdn->id), true, 0);
	}
	catch (CPHP\REST\NotFoundException $e)
	{
		return 0;
	}
	
	$lowest = null;
	
	foreach($fqdn_permissions as $permission)
	{
		if($permission->access_level < $lowest || $lowest === null)
		{
			$lowest = $permission->access_level;
		}
		
		if($resource->type === "user")
		{
			try
			{
				$user_permissions = $resource->user->ListPermissions(array("fqdn" => $fqdn->id), true, 0);
				
				foreach($user_permissions as $user_permission)
				{
					if($user_permission->access_level < $lowest)
					{
						$lowest = $user_permission->access_level;
					}
				}
			}
			catch (CPHP\REST\NotFoundException $e)
			{
				/* There are no permissions for this user on this FQDN! */
				return 0;
			}
		}
	}
	
	return $lowest;
});

$API->RegisterHandler("room", "notify", function($api, $room) {
	$allowed = ($api->_keypair->access_level >= 150) || ($room->fqdn->id === $api->_keypair->user->fqdn->id && $keypair->access_level >= 50);
	
	if($allowed !== true)
	{
		throw new CPHP\REST\NotAuthorizedException("You do not have the required access to perform that operation.");
	}
	
	$handler = new CPHPFormHandler($_POST, true);
	
	try
	{
		$handler
			->RequireNonEmpty("message")
			->Done();
	}
	catch (FormValidationException $e)
	{
		/* FIXME: Throw HTTP error for invalid input.. 410? */
	}
	
	$context = new ZMQContext();
	$query_socket = new ZMQSocket($context, ZMQ::SOCKET_PUSH);
	$query_socket->connect("tcp://127.0.0.1:18081");

	$payload = array(
		"type" => "room_notification",
		"args" => array(
			"room" => $room->jid,
			"color" => $handler->GetValue("color", "yellow"),
			"message" => $handler->GetValue("message"),
			"notify" => $handler-> GetValue("notify", "0"),
			"message_format" => $handler->GetValue("message_format", "html")
		)
	);
	
	$query_socket->send(json_encode($payload));
	
	return true;
});

$API->RegisterHandler("user", "authenticate", function($api, $user){
	$allowed = ($api->_keypair->access_level >= 150) || ($user->id === $api->_keypair->user->id && $keypair->access_level >= 50);
	
	if($allowed !== true)
	{
		throw new CPHP\REST\NotAuthorizedException("You do not have the required access to perform that operation.");
	}
	
	$handler = new CPHPFormHandler($_POST, true);
	
	try
	{
		$handler
			->RequireNonEmpty("password")
			->Done();
	}
	catch (FormValidationException $e)
	{
		throw new CPHP\REST\BadDataException("No password was provided.");
	}
	
	$provided_hash = base64_encode(pbkdf2("sha256", $handler->GetValue("password"), base64_decode($user->salt), 30000, 32, true));
	$correct_hash = $user->hash;
	
	return $api->ConstantTimeCompare($provided_hash, $correct_hash);
});

$API->RegisterHandler("user", "set_password", function($api, $user){
	$allowed = ($api->_keypair->access_level >= 150) || ($api->_keypair->user->fqdn->id === $user->fqdn->id && $api->_keypair->access_level >= 100);
	
	if($allowed !== true)
	{
		throw new CPHP\REST\NotAuthorizedException("You do not have the required access to perform that operation.");
	}
	
	$handler = new CPHPFormHandler($_POST, true);
	
	try
	{
		$handler
			->RequireNonEmpty("password")
			->Done();
	}
	catch (FormValidationException $e)
	{
		throw new CPHP\REST\BadDataException("No password was provided.");
	}
	
	$salt = base64_encode(mcrypt_create_iv(24, MCRYPT_DEV_URANDOM));
	$hash = base64_encode(pbkdf2("sha256", $handler->GetValue("password"), base64_decode($salt), 30000, 32, true));
	
	$user->hash = $hash;
	$user->salt = $salt;
	$user->DoCommit(true);
	
	return true;
});

$API->RegisterHandler("user", "get_api_key", function($api, $user){
	$allowed = ($api->_keypair->access_level >= 150) || ($user->id === $api->_keypair->user->id && $keypair->access_level >= 50);
	
	if($allowed !== true)
	{
		throw new CPHP\REST\NotAuthorizedException("You do not have the required access to perform that operation.");
	}
	
	$handler = new CPHPFormHandler($_GET, true);
	
	try
	{
		$handler
			->RequireNonEmpty("description")
			->Done();
	}
	catch (FormValidationException $e)
	{
		throw new CPHP\REST\BadDataException("No description was provided.");
	}
	
	try
	{
		$keypairs = $user->ListApiKeys(array("description" => $handler->GetValue("description")));
		return $keypairs[0];
	}
	catch (CPHP\REST\NotFoundException $e)
	{
		/* The key with the given description does not exist yet; create it. */
		$keypair = $user->ApiKey();
		$keypair->description = $handler->GetValue("description");
		$keypair->type = "user";
		$keypair->api_id = random_string(16);
		$keypair->api_key = random_string(24);
		$keypair->DoCommit();
		
		$permission = $keypair->Permission();
		$permission->fqdn = $keypair->user->fqdn;
		$permission->access_level = $handler->GetValue("access_level", 100);
		$permission->DoCommit();
		
		/* Reload keypair object to re-calculate access level... */
		$filters = array();
		$filters[$keypair->GetPrimaryIdField()] = $keypair->GetPrimaryId();
		$keypair = $api->ObtainResource("api_key", $filters, null, false, $keypair->chain, false, $keypair);
		
		return $keypair;
	}
});

$API->RegisterAuthenticator("affiliation", function($api, $affiliation, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($affiliation->room->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 10);
		case "create":
		case "delete":
		case "update":
			/* FIXME: Also let channel admins set this. */
			return ($keypair->user->id === $affiliation->room->owner->id);
	}
});

$API->RegisterAuthenticator("fqdn", function($api, $fqdn, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 10);
		case "create":
		case "delete":
			return ($keypair->access_level >= 150);
		case "update":
			return ($keypair->access_level >= 150)
				|| ($fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100);
	}
});

$API->RegisterAuthenticator("fqdn_setting", function($api, $setting, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($setting->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 75);
		case "create":
		case "delete":
		case "update":
			return ($keypair->access_level >= 150)
				|| ($setting->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100);
	}
});

$API->RegisterAuthenticator("room", function($api, $room, $keypair, $action) {
	/* If the room is private and the user is not a member, they can't do
	 * anything with it. */
	if($room->is_private)
	{
		try
		{
			$affiliations = $room->ListAffiliations(array("user" => $keypair->user->id));
		}
		catch (CPHP\REST\NotFoundException $e)
		{
			/* Definitely not. */
			return false;
		}
		
		$is_member = false;
		
		foreach($affiliations as $affiliation)
		{
			$is_member = $is_member || (in_array($affiliation->affiliation, array("owner", "admin", "member")));
		}
		
		if(!$is_member)
		{
			/* Nope. */
			return false;
		}
	}
	
	switch($action)
	{
		case "get":
			return ($room->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 10);
		case "create":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($room->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100);
		case "update":
			return ($keypair->access_level >= 150)
				|| ($room->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100)
				|| ($room->owner->id == $keypair->user->id && $keypair->access_level >= 50);
	}
});

$API->RegisterAuthenticator("user", function($api, $user, $keypair, $action) {
	/* We need to do a bit of a hack here; we can't call magic methods recursively
	 * from within themselves, so we manually retrieve the relevant user object,
	 * bypassing the authentication for that entirely. */
	try
	{
		$keypair_user = $api->ObtainResource("user", array("id" => $keypair->data["user"]), array(), true);
	}
	catch (CPHP\REST\NotFoundException $e)
	{
		/* This is only okay if the API key is a server key, as it has no
		 * user associated with it. */
		if($keypair->type === "user")
		{
			/* The keypair is a user keypair, this is not supposed to happen. */
			throw $e;
		}
	}
	
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($user->fqdn->id === $keypair_user->fqdn->id && $keypair->access_level >= 10);
		case "create":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($user->fqdn->id === $keypair_user->fqdn->id && $keypair->access_level >= 100);
		case "update":
			if(($keypair->access_level >= 150)
				|| ($user->fqdn->id === $keypair_user->fqdn->id && $keypair->access_level >= 100))
			{
				return true;
			}
			else
			{
				if($user->id === $keypair_user->id)
				{
					/* The user should only be allowed to set these particular attributes. */
					$allowed_attributes = array("nickname", "email_address", "first_name", "last_name", "job_title", "mobile_number");
					
					foreach($user->data as $attribute => $value)
					{
						if(!in_array($attribute, $allowed_attributes))
						{
							return false;
						}
					}
					
					return true;
				}
				else
				{
					return false;
				}
			}
	}
});

$API->RegisterAuthenticator("user_setting", function($api, $setting, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($setting->user->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 10);
		case "update":
		case "create":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($setting->user->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 50);
	}
});

$API->RegisterAuthenticator("api_key", function($api, $api_key, $keypair, $action) {
	switch($action)
	{
		case "get":
		case "create":
		case "update":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($api_keypair->user->id === $keypair->user->id && $keypair->access_level >= 50);
	}
});

$API->RegisterAuthenticator("api_permission", function($api, $permission, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($permission->keypair->user->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 10)
				|| ($permission->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 75);
		case "update":
		case "create":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($permission->keypair->user->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 50)
				|| ($permission->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100);
	}
});

$API->RegisterAuthenticator("user_permission", function($api, $permission, $keypair, $action) {
	switch($action)
	{
		case "get":
			return ($keypair->access_level >= 150)
				|| ($permission->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 75);
		case "update":
		case "create":
		case "delete":
			return ($keypair->access_level >= 150)
				|| ($permission->fqdn->id === $keypair->user->fqdn->id && $keypair->access_level >= 100);
	}
});

$API->ProcessRequest();

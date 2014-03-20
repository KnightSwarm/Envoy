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

use CPHP\REST;

function get_fqdn_access_level($fqdn, $keypair)
{
	$api_permissions = $keypair->ListPermissions(array("fqdn" => $fqdn->id));
	$user_permissions = $keypair->user->ListPermissions(array("fqdn" => $fqdn->id));
	
	$lowest_level = false;
	
	/* We can merge the arrays, since both API permissions and user permissions
	 * expose roughly the same interface. */
	foreach(array_merge($api_permissions, $user_permissions) as $permission)
	{
		/* Retrieve the original value, rather than the enum representation. *//
		$level = $api->EnumValue("access_level_enum", $permission->access_level);
		
		if($lowest_level === false || $level < $lowest_level)
		{
			$lowest_level = $level;
		}
	}
	
	if($lowest_level === false)
	{
		/* No permissions were found... */
		return 0;
	}
	else
	{
		return $lowest_level;
	}
}

$API = new API();
$API->LoadConfiguration("../api.json");

/* Possible actions:
 * get (retrieve)
 * update (change)
 * create (new item)
 * delete (existing item)
 */

$API->RegisterAuthenticator("fqdn", function($fqdn, $keypair, $action) {
	if($write === false)
	{
		/* The user must have read access to the FQDN. */
		return (get_fqdn_access_level($fqdn, $keypair) >= $API->EnumValue("access_level_enum", "read"));
	}
	else
	{
		/* The owner of the keypair must have administrative write access to
		 * the FQDN. */
		return (get_fqdn_access_level($fqdn, $keypair) >= $API->EnumValue("access_level_enum", "administrative"));
	}
});

$API->RegisterAuthenticator("user", function($user, $keypair, $action) {
	$access_level = get_fqdn_access_level($user->fqdn, $keypair);
	if($user->id == $keypair->user->id)
	{
		if($write === false || $access_level >= $API->EnumValue("access_level_enum", "write"))
		{
			return true;
		}
	}
	elseif($write === false && $access_level >= $API->EnumValue("access_level_enum", "administrative_read"))
	{
		return true;
	}
	elseif($access_level >= $API->EnumValue("access_level_enum", "administrative"))
	{
		return true;
	}
	
	return false;
});

$API->RegisterAuthenticator("room", function($room, $keypair, $action) {
	/* Either the room must be public, or the owner of the keypair must have at
	 * least a "member" affiliation with the room, or the owner of the keypair must
	 * have administrative access within the FQDN. */
	if($write === false)
	{
		if($room->is_public === true || get_fqdn_access_level($room->fqdn, $keypair) >= $API->EnumValue("access_level_enum", "administrative_read"))
		{
			return true;
		}
		else
		{
			foreach($room->ListAffiliations(array("user" => $keypair->user->id)) as $affiliation)
			{
				if(in_array($affiliation->affiliation, array("owner", "admin", "member")))
				{
					return true;
				}
			}
			
			/* If no matches... */
			return false;
		}
	}
	else
	{
		/* The owner of the keypair must either have an admin or owner
		 * affiliation with the room, or have administrative write access
		 * within the FQDN. */
		if(get_fqdn_access_level($room->fqdn, $keypair) >= $API->EnumValue("access_level_enum", "administrative"))
		{
			return true;
		}
		else
		{
			foreach($room->ListAffiliations(array("user" => $keypair->user->id)) as $affiliation)
			{
				if(in_array($affiliation->affiliation, array("owner", "admin")))
				{
					return true;
				}
			}
			
			/* If no matches... */
			return false;
		}
	}
});

$API->RegisterAuthenticator("affiliation", function($affiliation, $keypair, $action) {
	if($write === false)
	{
		/* Either the affliation must belong to the owner of the keypair, or the affiliation
		 * must belong to a public room, or the owner of the keypair must have
		 * administrative access within the FQDN. */
		return (($user->id == $keypair->user->id) || (get_fqdn_access_level($user->fqdn, $keypair) >= $API->EnumValue("access_level_enum", "read")));
	}
	else
	{
		/* Either the owner of the keypair must have an admin or owner
		 * position in the room that the affiliation belongs to, or the owner
		 * of the keypair must have administrative access within the FQDN. */
		if(get_fqdn_access_level($room->fqdn, $keypair) >= $API->EnumValue("access_level_enum", "administrative"))
		{
			return true;
		}
		else
		{
			foreach($affiliation->room->ListAffiliations(array("user" => $keypair->user->id)) as $affiliation)
			{
				if(in_array($affiliation->affiliation, array("owner", "admin")))
				{
					return true;
				}
			}
			
			/* If no matches... */
			return false;
		}
	}
});

$API->RegisterAuthenticator("api_key", function($api_key, $keypair, $action) {
	$access_level = get_fqdn_access_level($api_key->user->fqdn, $keypair);
	if($api_key->user->id == $keypair->user->id)
	{
		if($write === false || $access_level >= $API->EnumValue("access_level_enum", "write"))
		{
			return true;
		}
	}
	elseif($write === false && $access_level >= $API->EnumValue("access_level_enum", "administrative_read"))
	{
		return true;
	}
	elseif($access_level >= $API->EnumValue("access_level_enum", "administrative"))
	{
		return true;
	}
	
	return false;
});

$API->RegisterAuthenticator("api_permission", function($api_key, $keypair, $action) {
	$access_level = get_fqdn_access_level($api_key->user->fqdn, $keypair);
	if($api_key->user->id == $keypair->user->id)
	{
		if($write === false || $access_level >= $API->EnumValue("access_level_enum", "write"))
		{
			return true;
		}
	}
	elseif($write === false && $access_level >= $API->EnumValue("access_level_enum", "administrative_read"))
	{
		return true;
	}
	elseif($access_level >= $API->EnumValue("access_level_enum", "administrative"))
	{
		return true;
	}
	
	return false;
});


$API->RegisterDecoder("room", "jid", function($resource) {
	return $resource->roomname . "@" . $resource->fqdn->fqdn;
});

$API->RegisterDecoder("user", "jid", function($resource) {
	return $resource->username . "@" . $resource->fqdn->fqdn;
});

$API->RegisterHandler("room", "notify", function($room) {
	$handler = new CPHPFormHandler();
	
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

	$query_socket->send(json_encode(array(
		"type" => "room_notification",
		"args" => array(
			"room" => $room->jid,
			"color" => $handler->GetValue("color", "yellow"),
			"message" => $handler->GetValue("message"),
			"notify" => $handler-> GetValue("notify", "0"),
			"message_format" => $handler->GetValue("message_format", "html")
		)
	)));
});

/* Old API code below */

require("include/base.php");

if(empty($_SERVER['HTTP_ENVOY_API_ID']) || empty($_SERVER['HTTP_ENVOY_API_SIGNATURE']))
{
	header('WWW-Authenticate: EnvoyAPIKey realm="Envoy API"');
	http_status_code(401);
	echo(json_encode(array("error" => "You did not provide API credentials.")));
	die();
}

$uApiId = $_SERVER['HTTP_ENVOY_API_ID'];
$uApiSignature = $_SERVER['HTTP_ENVOY_API_SIGNATURE'];

try
{
	$sApiKeypair = ApiKeypair::CreateFromQuery("SELECT * FROM api_keys WHERE `ApiId` = :ApiId", array(":ApiId" => $uApiId), 60, true);
	
	/* Remove query string from URI for signing. */
	$requestpath = $_SERVER['REQUEST_URI'];
	if(strpos($requestpath, "?") !== false)
	{
		list($requestpath, $bogus) = explode("?", $requestpath, 2);
	}
	
	$authorized = verify_request($uApiSignature, $sApiKeypair->uApiKey, strtoupper($_SERVER['REQUEST_METHOD']), $requestpath, $_GET, $_POST);
}
catch (NotFoundException $e)
{
	$authorized = false;
}

if($authorized === false)
{
	header('WWW-Authenticate: EnvoyAPIKey realm="Envoy API"');
	http_status_code(401);
	echo(json_encode(array("error" => "The API credentials you provided are invalid.")));
	die();
}

$sResponse = array();
$sCode = 200;

$router = new CPHPRouter();

$router->allow_slash = true;
$router->ignore_query = true;

$router->routes = array(
	0 => array(
		"^/$"		=> "list.php",
		"^/echo$"	=> array(
			"methods"	=> array("post", "get"),
			"target"	=> "modules/echo.php"
		),
		"^/user/register$"	=> array(
			"methods"	=> "post",
			"target"	=> "modules/user/register.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/user/lookup$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/lookup.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/user/authenticate$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/authenticate.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/user/settings/lookup"=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/settings/lookup.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/user/settings/set"=> array(
			"methods"	=> "post",
			"target"	=> "modules/user/settings/set.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/user/api-key"=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/api_key.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/room$"		=> array(
			"methods"	=> "get",
			"target"	=> "modules/room/list.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/room/lookup$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/room/lookup.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/room/create"	=> array(
			"methods"	=> "post",
			"target"	=> "modules/room/create.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		),
		"^/fqdn$"		=> array(
			"methods"	=> "get",
			"target"	=> "modules/fqdn/list.php"
		),
		"^/fqdn/create$"	=> array(
			"methods"	=> "post",
			"target"	=> "modules/fqdn/create.php"
		),
		"^/fqdn/lookup$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/fqdn/lookup.php",
			"authenticator"	=> "authenticators/fqdn_exists.php",
			"auth_error"	=> ""
		)
	)
);

try
{
	$router->RouteRequest();
}
catch (RouterException $e)
{
	http_status_code(404);
	echo(json_encode(array("error" => "The specified path is invalid.", "type" => "path")));
	die();
}
catch (MissingParameterException $e)
{
	http_status_code(400);
	echo(json_encode(array("error" => $e->getMessage())));
	die();
}
catch (InvalidFqdnException $e)
{
	http_status_code(422);
	echo(json_encode(array("error" => $e->getMessage())));
	die();
}
catch (NotAuthorizedException $e)
{
	http_status_code(403);
	echo(json_encode(array("error" => $e->getMessage())));
	die();
}
catch (ResourceNotFoundException $e)
{
	http_status_code(404);
	echo(json_encode(array("error" => $e->getMessage(), "type" => "resource")));
	die();
}
catch (AlreadyExistsException $e)
{
	http_status_code(409);
	echo(json_encode(array("error" => $e->getMessage())));
	die();
}
catch (InvalidParameterException $e)
{
	http_status_code(400);
	echo(json_encode(array("error" => $e->getMessage())));
	die();
}
catch (Exception $e)
{
	echo($e);
	/* TODO: Log error, this should really never happen. */
	http_status_code(500);
	echo(json_encode(array("error" => "An unknown error occurred.")));
	die();
}

http_status_code($sCode);

echo(json_encode(array(
	"response" => $sResponse
)));

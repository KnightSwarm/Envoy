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

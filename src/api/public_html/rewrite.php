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

if(empty($_SERVER['HTTP_ENVOY_API_ID']) || empty($_SERVER['HTTP_ENVOY_API_KEY']))
{
	header('WWW-Authenticate: EnvoyAPIKey realm="Envoy API"');
	http_status_code(401);
	echo(json_encode(array("error" => "You did not provide API credentials.")));
	die();
}

$uApiId = $_SERVER['HTTP_ENVOY_API_ID'];
$uApiKey = $_SERVER['HTTP_ENVOY_API_KEY'];

try
{
	$sApiKeypair = ApiKeypair::CreateFromQuery("SELECT * FROM api_keys WHERE `ApiId` = :ApiId AND `ApiKey` = :ApiKey", array(":ApiId" => $uApiId, ":ApiKey" => $uApiKey), 60, true);
}
catch (NotFoundException $e)
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
			"target"	=> "modules/user/register.php"
		),
		"^/user/lookup$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/lookup.php"
		),
		"^/user/authenticate$"	=> array(
			"methods"	=> "get",
			"target"	=> "modules/user/authenticate.php"
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

http_status_code($sCode);

echo(json_encode(array(
	"response" => $sResponse
)));

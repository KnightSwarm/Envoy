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

$sPageTitle = "";
$sPageContents = "";

$router = new CPHPRouter();

$router->allow_slashes = true;
$router->ignore_query = true;

$router->routes = array(
	0 => array(
		"^/$" => array(
			"target" => "modules/dashboard.php",
			"authenticator" => "authenticators/logged_in.php",
			"auth_error" => "modules/error/not_logged_in.php"
		),
		"^/login$" => array(
			"target" => "modules/login.php"
		),
		"^/logout$" => array(
			"target" => "modules/logout.php",
			"methods" => "post",
			"authenticator" => "authenticators/logged_in.php",
			"auth_error" => "modules/error/not_logged_in.php"
		),
	)
);

$router->RouteRequest();

echo(NewTemplater::Render("layout", $locale->strings, array("title" => $sPageTitle, "contents" => $sPageContents)));

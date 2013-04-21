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

if(strtolower($_SERVER["REQUEST_METHOD"]) == "get" && !empty($_GET['fqdn']))
{
	$fqdn = $_GET['fqdn'];
}
elseif(strtolower($_SERVER["REQUEST_METHOD"]) == "post" && !empty($_POST['fqdn']))
{
	$fqdn = $_POST['fqdn'];
}
else
{
	throw new InvalidFqdnException("No FQDN specified.");
}

try
{
	Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(":Fqdn" => $fqdn), 5);
}
catch (NotFoundException $e)
{
	throw new InvalidFqdnException("The specified FQDN does not exist.");
}

$sRouterAuthenticated = true;

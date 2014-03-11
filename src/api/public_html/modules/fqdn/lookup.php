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

$sApiKeypair->RequireAdministrativeReadAccess($_GET['fqdn']);

try
{
	$sFqdn = Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(
	                               ":Fqdn" => $_GET['fqdn']), 10, true);
}
catch (NotFoundException $e)
{
	throw new ResourceNotFoundException("The specified FQDN does not exist.");
}

$sResponse = array(
	"name"		=> $sFqdn->uName,
	"description"	=> $sFqdn->uDescription,
	"owner"		=> array(
		"id"		=> $sFqdn->sOwner->sId,
		"username"	=> $sFqdn->sOwner->uUsername,
		"name" => $sFqdn->sOwner->uFullName
	)
);

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

if(empty($_GET['roomname']))
{
	throw new MissingParameterException("Missing required roomname field.");
}

$sApiKeypair->RequireAdministrativeReadAccess($_GET['fqdn']);

try
{
	$sRoom = Room::CreateFromQuery("SELECT * FROM rooms WHERE `Node` = :Node AND `FqdnId` = :Fqdn", array(
	                               ":Node" => $_GET['roomname'], ":Fqdn" => $sCurrentFqdn->sId), 10, true);
}
catch (NotFoundException $e)
{
	throw new ResourceNotFoundException("The specified room does not exist.");
}

$sResponse = array(
	"roomname"	=> $sRoom->uNode,
	"friendlyname"	=> $sRoom->uName,
	"description"	=> $sRoom->uDescription,
	"private"	=> $sRoom->sIsPrivate,
	"archived"	=> $sRoom->sIsArchived,
	"owner"		=> $sRoom->uOwnerId,
	"creationdate"	=> $sRoom->sCreationDate,
	"archivaldate"	=> $sRoom->sArchivalDate,
	"usercount"	=> $sRoom->uLastUserCount
);

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

if(empty($_POST['fqdn']) || empty($_POST['roomname']) || empty($_POST['name']) || empty($_POST['owner']) || !isset($_POST['private']))
{
	throw new MissingParameterException("Missing one or more required fields.");
}

$sApiKeypair->RequireAdministrativeAccess($_POST['fqdn']);

try
{
	$sExistingRoom = Room::CreateFromQuery("SELECT * FROM rooms WHERE `FqdnId` = :FqdnId AND `Node` = :Node", array(
	                                       ":FqdnId" => $sCurrentFqdn->sId, ":Node" => $_POST['roomname']), 0);
	$found = true;
}
catch (NotFoundException $e)
{
	$found = false;
}

if($found === true)
{
	throw new AlreadyExistsException("The specified room already exists.");
}

try
{
	$sOwner = User::CreateFromQuery("SELECT * FROM users WHERE `Id` = :Id", array("Id" => $_POST['owner']), 0, true);
}
catch (NotFoundException $e)
{
	throw new InvalidParameterException("The specified owner does not exist.");
}

$sRoom = new Room();
$sRoom->uNode = $_POST['roomname'];
$sRoom->uName = $_POST['name'];
$sRoom->uDescription = (!empty($_POST['description'])) ? $_POST['description'] : "";
$sRoom->uFqdnId = $sCurrentFqdn->sId;
$sRoom->uOwnerId = $sOwner->sId;
$sRoom->uLastUserCount = 0;
$sRoom->uIsPrivate = !empty($_POST['private']);
$sRoom->uIsArchived = 0;
$sRoom->uCreationDate = time();
$sRoom->InsertIntoDatabase();

$sResponse = array("room_id" => $sRoom->sId);

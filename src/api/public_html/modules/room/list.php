<?php
/* Copyright 2014 by Sven Slootweg <admin@cryto.net>
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

/* If the user is an FQDN administrator, we will provide all rooms in
 * the FQDN. If he is not, we will only provide the public rooms, and
 * the rooms that the user is a member of. */

if($sApiKeypair->GetAccessLevel($_GET["fqdn"]) >= ApiPermission::ADMINISTRATIVE_READ)
{
	/* All rooms. */
	$sRooms = Room::CreateFromQuery("SELECT * FROM rooms WHERE `FqdnId` = :FqdnId", array("FqdnId" => $sCurrentFqdn->sId));
}
else
{
	/* Only public and user-accessible rooms. */
	try {
		$sPublicRooms = Room::CreateFromQuery("SELECT * FROM rooms WHERE `FqdnId` = :FqdnId AND `IsPrivate` = 0", array("FqdnId" => $sCurrentFqdn->sId));
	} catch (NotFoundException $e) { /* pass */ $sPublicRooms = array(); }
	
	$sAvailablePrivateRooms = array();
	
	try {
		$sPrivateRooms = Room::CreateFromQuery("SELECT * FROM rooms WHERE `FqdnId` = :FqdnId AND `IsPrivate` = 1", array("FqdnId" => $sCurrentFqdn->sId));
	} catch (NotFoundException $e) { /* pass */ $sPrivateRooms = array(); }
	
	foreach($sPrivateRooms as $sRoom)
	{
		try {
			$sAffiliation = Affiliation::CreateFromQuery("SELECT * FROM affiliations WHERE `RoomId` = :RoomId AND `UserId` = :UserId", array("RoomId" => $sRoom->sId, "UserId" => $sApiKeypair->sUser->sId), 60, true);
			
			if($sAffiliation->sAffiliation == Affiliation::OWNER || $sAffiliation->sAffiliation == Affiliation::ADMIN || $sAffiliation->sAffiliation == Affiliation::MEMBER)
			{
				/* User can see this room. */
				$sAvailablePrivateRooms[] = $sRoom;
			}
		} catch (NotFoundException $e) { /* No affiliation, pass */ }
	}
	
	/* The final list... */
	$sRooms = array_merge($sPublicRooms, $sAvailablePrivateRooms);
}
 
$sRoomList = array();

foreach($sRooms as $sRoom)
{
	$sRoomList[] = array(
		"id" => $sRoom->uJid, /* alias for 'jid', to make client libraries happy */ 
		"jid" => $sRoom->uJid,
		"roomname"	=> $sRoom->uNode,
		"friendlyname"	=> $sRoom->uName,
		"description"	=> $sRoom->uDescription,
		"private"	=> $sRoom->sIsPrivate,
		"archived"	=> $sRoom->sIsArchived,
		"owner"		=> array(
			"id" => $sRoom->sOwner->sId,
			"username" => $sRoom->sOwner->uUsername,
			"name" => $sRoom->sOwner->uFullName
		),
		"creationdate"	=> $sRoom->sCreationDate,
		"archivaldate"	=> $sRoom->sArchivalDate,
		"usercount"	=> $sRoom->uLastUserCount
	);
}
 

$sResponse = $sRoomList;

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

if(empty($_GET['roomname']))
{
	throw new MissingParameterException("Missing required roomname field.");
}

$sRoom = Room::GetByRoomname($_GET["roomname"]);

$sAffiliationList = array();

foreach(Affiliation::CreateFromQuery("SELECT * FROM affiliations WHERE `RoomId` = :RoomId", array("RoomId" => $sRoom->sId)) as $sAffiliation)
{
	$sAffiliationList[] = array(
		"id" => $sAffiliation->sId,
		"room_jid" => $sAffiliation->sRoom->uJid,
		"user_jid" => $sAffiliation->sUser->uJid,
		"affiliation" => $sAffiliation->sAffiliation
	);
}

$sResponse = $sAffiliationList;

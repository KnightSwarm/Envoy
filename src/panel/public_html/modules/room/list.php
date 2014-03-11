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

$sRooms = array();

$sFqdn = $sAPI->Fqdn($router->uParameters[1]);

foreach($sFqdn->ListRooms() as $sRoom)
{
	$sRooms[] = array(
		"jid" => htmlspecialchars($sRoom->jid), 
		"name" => htmlspecialchars($sRoom->friendly_name), 
		"owner" => htmlspecialchars($sRoom->owner_name),
		"owner_jid" => htmlspecialchars($sRoom->owner_jid),
		"roomname" => htmlspecialchars($sRoom->roomname)
	);
}

$sPageContents = NewTemplater::Render("rooms/list", $locale->strings, array("rooms" => $sRooms, "fqdn" => $sFqdn->fqdn));

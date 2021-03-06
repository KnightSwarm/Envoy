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

$sRoom = $API->Fqdn($router->uParameters[1])->Room($router->uParameters[2]);

$sPageContents = NewTemplater::Render("rooms/lookup", $locale->strings, array(
	"fqdn" => htmlspecialchars($sRoom->fqdn->fqdn),
	"name" => htmlspecialchars($sRoom->name),
	"roomname" => htmlspecialchars($sRoom->roomname),
	"jid" => htmlspecialchars($sRoom->jid),
	"owner" => htmlspecialchars($sRoom->owner->full_name),
	"owner-jid" => htmlspecialchars($sRoom->owner->jid),
	"creation-date" => local_from_unix($sRoom->creation_date, $locale->datetime_long),
	"private" => $sRoom->is_private,
	"archived" => $sRoom->is_archived,
));

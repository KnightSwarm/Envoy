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

$sUsers = array();

$sFqdn = $API->Fqdn($router->uParameters[1]);

foreach($sFqdn->ListUsers() as $sUser)
{
	$sUsers[] = array(
		"id" => htmlspecialchars($sUser->id),
		"jid" => htmlspecialchars($sUser->jid),
		"name" => htmlspecialchars($sUser->full_name), 
		"title" => htmlspecialchars($sUser->job_title), 
		"username" => htmlspecialchars($sUser->username),
		"email" => htmlspecialchars($sUser->email_address),
		"phone" => htmlspecialchars($sUser->mobile_number),
		"status" => htmlspecialchars($sUser->status),
	);
}

$sPageContents = NewTemplater::Render("users/list", $locale->strings, array("users" => $sUsers, "fqdn" => $sFqdn->fqdn));

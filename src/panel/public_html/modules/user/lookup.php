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

$sUser = $API->Fqdn($router->uParameters[1])->User($router->uParameters[2]);

$sPageContents = NewTemplater::Render("users/lookup", $locale->strings, array(
	"username" => htmlspecialchars($sUser->username),
	"fqdn" => htmlspecialchars($sUser->fqdn->fqdn),
	"jid" => htmlspecialchars($sUser->jid),
	"name" => htmlspecialchars($sUser->full_name),
	"nickname" => htmlspecialchars($sUser->nickname),
	"job-title" => htmlspecialchars($sUser->job_title),
	"email" => htmlspecialchars($sUser->email_address),
	"phone" => htmlspecialchars($sUser->mobile_number),
	"status" => htmlspecialchars($sUser->status),
	"status-message" => htmlspecialchars($sUser->status_message),
	"active" => htmlspecialchars($sUser->is_active)
));

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

$sErrors = array();

if($router->uMethod == "post")
{
	$handler = new CPHPFormHandler();

	try
	{
		$handler
			->RequireNonEmpty("roomname")
			->RequireNonEmpty("name")
			->Done();
	}
	catch (FormValidationException $e)
	{
		$sErrors = $e->GetErrorMessages(array(
			"required" => array(
				"roomname" => "You must specify a room JID.",
				"name" => "You must specify a room name."
			)
		));
	}
	
	if(empty($sErrors))
	{
		$sRoom = $API->Fqdn($router->uParameters[1])->Room();
		$sRoom->roomname = $handler->GetValue("roomname");
		$sRoom->name = $handler->GetValue("name");
		$sRoom->description = $handler->GetValue("description", "");
		$sRoom->owner = $_SESSION["user_id"];
		$sRoom->is_private = 0;
		$sRoom->is_archived = 0;
		$sRoom->DoCommit();
		
		redirect("/fqdns/{$router->uParameters[1]}/rooms/{$sRoom->roomname}");
	}
}

$sPageContents = NewTemplater::Render("rooms/create", $locale->strings, array("errors" => $sErrors, "fqdn" => htmlspecialchars($router->uParameters[1])));

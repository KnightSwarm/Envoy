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
			->RequireNonEmpty("username")
			->RequireNonEmpty("password")
			//->RequireNonEmpty("email")
			->RequireNonEmpty("nickname")
			->ValidateEmail("email")
			->Done();
	}
	catch (FormValidationException $e)
	{
		$sErrors = $e->GetErrorMessages(array(
			"required" => array(
				"username" => "You must specify a username.",
				"password" => "You must specify a password.",
				"nickname" => "You must specify a nickname.",
			),
			"email" => array(
				"email" => "You must specify a valid e-mail address."
			)
		));
	}
	
	if(empty($sErrors))
	{
		$sUser = $API->Fqdn($router->uParameters[1])->User();
		$sUser->username = $handler->GetValue("username");
		$sUser->job_title = $handler->GetValue("title", "");
		$sUser->email_address = $handler->GetValue("email");
		$sUser->nickname = $handler->GetValue("nickname");
		$sUser->is_active = true;
		$sUser->DoCommit();
		
		$sUser->SetPassword(array("password" => $handler->GetValue("password")));
		
		redirect("/fqdns/{$router->uParameters[1]}/users/{$sUser->username}");
	}
}

$sPageContents = NewTemplater::Render("users/create", $locale->strings, array("errors" => $sErrors, "fqdn" => htmlspecialchars($router->uParameters[1])));

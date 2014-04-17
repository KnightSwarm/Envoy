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
$sUser = $API->User($_SESSION["jid"]);

if($router->uMethod == "post")
{
	$handler = new CPHPFormHandler();
	
	try
	{
		$handler
			->RequireNonEmpty("first_name")
			->RequireNonEmpty("nickname")
			->ValidateEmail("email")
			->Done();
	}
	catch (FormValidationException $e)
	{
		$sErrors = $e->GetErrorMessages(array(
			"required" => array(
				"first_name" => "You must specify at least a first name.",
				"nickname" => "You must specify a nickname."
			),
			"email" => array(
				"email" => "You must specify a valid e-mail address."
			)
		));
	}
	
	$sUser->first_name = $handler->GetValue("first_name");
	$sUser->last_name = $handler->GetValue("last_name");
	$sUser->email_address = $handler->GetValue("email");
	$sUser->mobile_number = $handler->GetValue("phone");
	$sUser->nickname = $handler->GetValue("nickname");
	$sUser->job_title = $handler->GetValue("job_title");
	$sUser->DoCommit();
	
	$sErrors[] = "The changes have been saved."; /* Not actually an error; easy workaround. */
}

$sPageContents = NewTemplater::Render("profile", $locale->strings, array(
	"first_name" => htmlspecialchars($sUser->first_name),
	"last_name" => htmlspecialchars($sUser->last_name),
	"phone" => htmlspecialchars($sUser->mobile_number),
	"email" => htmlspecialchars($sUser->email_address),
	"job_title" => htmlspecialchars($sUser->job_title),
	"nickname" => htmlspecialchars($sUser->nickname),
	"errors" => $sErrors
));

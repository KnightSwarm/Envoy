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

$sErrors = array();

if($router->uMethod == "post")
{
	/* Process login */
	$handler = new CPHPFormHandler();
	
	try
	{
		$handler
			->RequireNonEmpty("username")
			->RequireNonEmpty("password")
			->ValidateCustom("username", "The provided address is not a valid XMPP address.", function($key, $value){
				return filter_var($value, FILTER_VALIDATE_EMAIL) !== false;
			})
			->Done();
	}
	catch (FormValidationException $e)
	{
		$sErrors = $e->GetErrorMessages(array(
			"required" => array(
				"username" => "You must enter a username.",
				"password" => "You must enter a password."
			)
		));
	}
	
	if(empty($sErrors))
	{
		/* Actual authentication step */
		$sUser = $API->User($_POST["username"]);
		
		try
		{
			$sValid = ($sUser->Authenticate(array("password" => $_POST["password"])) === true);
		}
		catch (CPHP\REST\NotFoundException $e)
		{
			/* The user does not exist. */
			$sValid = false;
		}
		
		if($sValid === true)
		{
			/* Password was valid. We'll now retrieve the panel API keypair for
			 * this user - and create one if it doesn't exist yet - and we'll use
			 * that keypair for any subsequent requests. This way, we don't
			 * have to reimplement access controls, and can just rely on the
			 * access control in the API itself. */
			$sKeypair = $sUser->GetApiKey(array("description" => "Envoy Panel"));
			$_SESSION["jid"] = $sUser->jid;
			$_SESSION["username"] = $sUser->username;
			$_SESSION["fqdn"] = $sUser->fqdn->fqdn;
			$_SESSION["user_id"] = $sUser->id;
			$_SESSION["keypair_id"] = $sKeypair->id;
			$_SESSION["access_level"] = $sKeypair->access_level;
			$_SESSION["api_id"] = $sKeypair->api_id;
			$_SESSION["api_key"] = $sKeypair->api_key;
			
			redirect("/");
		}
		else
		{
			$sErrors[] = "The provided login details are incorrect.";
		}
	}
}

$sPageTitle = "Log in";
$sPageContents = NewTemplater::Render("login", $locale->strings, array("errors" => $sErrors));

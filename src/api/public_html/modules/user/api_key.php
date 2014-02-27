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

if(empty($_GET['username']))
{
	throw new MissingParameterException("Missing required username field.");
}

if(empty($_GET['description']))
{
	throw new MissingParameterException("Missing required description field.");
}

$authenticated = false;

try
{
	$sApiKeypair->RequireAdministrativeReadAccess($_GET['fqdn']);
	$authenticated = true;
}
catch (NotAuthorizedException $e)
{
	/* User does not have administrative read access to the FQDN;
	 * however, if the user is requesting his own API key, that's still
	 * okay. See code below. */
}

try
{
	$sUser = User::CreateFromQuery("SELECT * FROM users WHERE `Username` = :Username AND `Fqdn` = :Fqdn", array(
	                               ":Username" => $_GET['username'], ":Fqdn" => $_GET['fqdn']), 10, true);
	$user_found = true;
	
	if($sApiKeypair->sUser->sId === $sUser->sId)
	{
		$authenticated = true;
	}
}
catch (NotFoundException $e)
{
	/* FIXME: Possible information leak? Might reveal whether a user
	 * exists, even if there is no administrative FQDN read access. */
	throw new ResourceNotFoundException("The specified user does not exist.");
}

if($authenticated === false)
{
	throw NotAuthorizedException("You do not have administrative FQDN read access, and cannot retrieve API keys for another user.");
}
else
{
	try
	{
		$sKeypair = ApiKeypair::CreateFromQuery("SELECT * FROM api_keypairs WHERE `UserId` = :UserId AND `Description` = :Description", array("UserId" => $sUser->sId, "Description" => $_GET["description"]), 0, true)
	}
	catch (NotFoundException $e)
	{
		/* Do we need to create one if it doesn't exist yet? */
		if(isset($_GET["create"]) && $_GET["create"] == true)
		{
			try
			{
				/* To create a new API keypair on-the-spot, we need administrative
				 * write access to the FQDN as well. 
				 * TODO: Also allow write access for users to their own API keys;
				 * this needs more looking into wrt security first. */
				$sApiKeypair->RequireAdministrativeAccess();
			}
			catch (NotAuthorizedException $e)
			{
				/* Throw a more detailed exception. */
				throw NotAuthorizedException("The requested API key does not exist, and you do not have the administrative write access required to create it.");
			}
			
			$sKeypair = new ApiKeypair();
			$sKeypair->uUserId = $sUser->sId;
			$sKeypair->uType = ApiKeypair::USER;
			$sKeypair->GenerateKeypair();
			$sKeypair->uDescription = $_GET["description"];
			$sKeypair->InsertIntoDatabase();
		}
		else
		{
			throw NotFoundException("The requested API key was not found.");
		}
	}
	
	/* If we end up here, we found either an existing API key, or a
	 * newly created one. */
	
	$sResponse = array(
		"keypair_id" => $sKeypair->sId,
		"user_id" => $sKeypair->sUser->sId,
		"access_level" => $sKeypair->GetAccessLevel($_GET["fqdn"]),
		"api_id" => $sKeypair->sApiId,
		"api_key" => $sKeypair->sApiKey
	);
}

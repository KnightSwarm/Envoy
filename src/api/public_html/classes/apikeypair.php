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

class ApiKeypair extends CPHPDatabaseRecordClass
{
	public $table_name = "api_keys";
	public $fill_query = "SELECT * FROM api_keys WHERE `Id` = :Id";
	public $verify_query = "SELECT * FROM api_keys WHERE `Id` = :Id";
	
	public $prototype = array(
		'string' => array(
			'Description'		=> "Description",
			'ApiId'			=> "ApiId",
			'ApiKey'		=> "ApiKey"
		),
		'numeric' => array(
			'Type'			=> "Type",
			'UserId'		=> "UserId"
		),
		'user' => array(
			'User'			=> "UserId"
		)
	);
	
	const SERVER = 0;
	const USER = 1;
	
	public function HasMasterAccess()
	{
		try
		{
			$this->RequireMasterAccess();
			return true;
		}
		catch (NotAuthorizedException $e)
		{
			return false;
		}
	}
	
	public function GetAccessLevel($fqdn)
	{
		if($this->HasMasterAccess())
		{
			return 200;
		}
		
		$sFqdn = Fqdn::GetByFqdn($fqdn);
		
		try
		{
			$sApiPermission = ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = :FqdnId AND `ApiKeyId` = :ApiKeyId",
			                               array(":FqdnId" => $sFqdn->sId, ":ApiKeyId" => $this->sId), 5, true);
		}
		catch (NotFoundException $e)
		{
			/* Disallowed by API key access restriction */
			return 0;
		}
		
		if($this->sType == ApiKeypair::USER)
		{
			try
			{
				$sUserPermission = UserPermission::CreateFromQuery("SELECT * FROM user_permissions WHERE `FqdnId` = :FqdnId AND `UserId` = :UserId",
							       array(":FqdnId" => $sFqdn->sId, ":UserId" => $this->sUser->sId), 5, true);
			}
			catch (NotFoundException $e)
			{
				/* Disallowed by user access restriction */
				return 0;
			}
			
			return min($sUserPermission->sType, $sApiPermission->sType);
		}
		else
		{
			return $sApiPermission->sType;
		}
	}
	
	public function RequireAccessLevel($fqdn, $level, $error)
	{
		if($this->GetAccessLevel($fqdn) < $level)
		{
			throw new NotAuthorizedException($error);
		}
	}
	
	public function RequireMasterAccess()
	{
		if($this->sType == ApiKeypair::USER)
		{
			/* User API keys cannot have master access */
			throw new NotAuthorizedException("User API keys cannot have master access.");
		}
		else
		{
			try
			{
				ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = 0 AND `ApiKeyId` = :ApiKeyId AND `Type` >= 200",
							       array(":ApiKeyId" => $this->sId));
			}
			catch (NotFoundException $e)
			{
				/* Disallowed by API key access restriction */
				throw new NotAuthorizedException("You do not have master access.");
			}
		}
	}
	
	public function RequireAdministrativeAccess($fqdn)
	{
		$this->RequireAccessLevel($fqdn, 100, "You do not have administrative access to this FQDN.");
	}

	public function RequireAdministrativeReadAccess($fqdn)
	{
		$this->RequireAccessLevel($fqdn, 75, "You do not have administrative read access to this FQDN.");
	}
	
	public function RequireWriteAccess($fqdn)
	{
		$this->RequireAccessLevel($fqdn, 50, "You do not have write access to this FQDN.");
	}
	
	public function RequireReadAccess($fqdn)
	{
		$this->RequireAccessLevel($fqdn, 10, "You do not have read access to this FQDN.");
	}
	
	public function GenerateKeypair()
	{
		/* FIXME: CPHP should use openssl_pseudo_random_bytes or mt_rand
		 * rather than rand(). */
		$this->uApiId = random_string(16);
		$this->uApiKey = random_string(24);
	}
}

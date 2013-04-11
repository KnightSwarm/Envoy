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
	
	public function RequireAdministrativeAccess($fqdn)
	{
		$sFqdn = Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(":Fqdn" => $fqdn), 60, true);
		
		try
		{
			ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = :FqdnId AND `ApiKeyId` = :ApiKeyId AND `Type` >= 100",
			                               array(":FqdnId" => $sFqdn->sId, ":ApiKeyId" => $this->sId));
		}
		catch (NotFoundException $e)
		{
			throw new NotAuthorizedException("You do not have administrative access to this FQDN.");
		}
	}

	public function RequireAdministrativeReadAccess($fqdn)
	{
		$sFqdn = Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(":Fqdn" => $fqdn), 60, true);
		
		try
		{
			ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = :FqdnId AND `ApiKeyId` = :ApiKeyId AND `Type` >= 75",
			                               array(":FqdnId" => $sFqdn->sId, ":ApiKeyId" => $this->sId));
		}
		catch (NotFoundException $e)
		{
			throw new NotAuthorizedException("You do not have administrative read access to this FQDN.");
		}
	}
	
	public function RequireWriteAccess($fqdn)
	{
		$sFqdn = Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(":Fqdn" => $fqdn), 60, true);
		
		try
		{
			ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = :FqdnId AND `ApiKeyId` = :ApiKeyId AND `Type` >= 50",
			                               array(":FqdnId" => $sFqdn->sId, ":ApiKeyId" => $this->sId));
		}
		catch (NotFoundException $e)
		{
			throw new NotAuthorizedException("You do not have write access to this FQDN.");
		}
	}
	
	public function RequireReadAccess($fqdn)
	{
		$sFqdn = Fqdn::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(":Fqdn" => $fqdn), 60, true);
		
		try
		{
			ApiPermission::CreateFromQuery("SELECT * FROM api_permissions WHERE `FqdnId` = :FqdnId AND `ApiKeyId` = :ApiKeyId AND `Type` >= 10",
			                               array(":FqdnId" => $sFqdn->sId, ":ApiKeyId" => $this->sId));
		}
		catch (NotFoundException $e)
		{
			throw new NotAuthorizedException("You do not have read access to this FQDN.");
		}
	}
}
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

if(empty($_POST['fqdn']) || empty($_POST['name']) || empty($_POST['admin_username']) || empty($_POST['admin_password']))
{
	throw new MissingParameterException("Missing one or more required fields.");
}

try
{
	$sExistingFqdn = User::CreateFromQuery("SELECT * FROM fqdns WHERE `Fqdn` = :Fqdn", array(
	                                       ":Fqdn" => $_POST['fqdn']), 0);
	$found = true;
}
catch (NotFoundException $e)
{
	$found = false;
}

if($found === true)
{
	throw new AlreadyExistsException("The specified FQDN already exists.");
}


$sFqdn = new Fqdn(0);
$sFqdn->uFqdn = $_POST['fqdn'];
$sFqdn->uName = $_POST['name'];
$sFqdn->uDescription = (!empty($_POST['description'])) ? $_POST['description'] : "";
$sFqdn->uOwnerId = 0;
$sFqdn->InsertIntoDatabase();

$sUser = new User(0);
$sUser->uUsername = $_POST['admin_username'];
$sUser->uFqdn = $_POST['fqdn'];
$sUser->uFqdnId = $sFqdn->sId;
$sUser->uPassword = $_POST['admin_password'];
$sUser->uActive = true;
$sUser->GenerateSalt();
$sUser->GenerateHash();
$sUser->InsertIntoDatabase();

$sFqdn->uOwnerId = $sUser->sId;
$sFqdn->InsertIntoDatabase();

/* TODO: Re-generate ejabberd configuration to serve this FQDN. */

$sUserPermission = new UserPermission(0);
$sUserPermission->uFqdnId = $sFqdn->sId;
$sUserPermission->uUserId = $sUser->sId;
$sUserPermission->uType = 100;
$sUserPermission->InsertIntoDatabase();

$sResponse = array("fqdn_id" => $sFqdn->sId ,"admin_user_id" => $sUser->sId);

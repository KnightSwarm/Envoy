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

if(empty($_POST['username']))
{
	throw new MissingParameterException("Missing required username field.");
}

if(empty($_POST['key']) || empty($_POST['value']))
{
	throw new MissingParameterException("Missing required 'key' field.");
}

$sApiKeypair->RequireAdministrativeAccess($_POST['fqdn']);

try
{
	$sUser = User::CreateFromQuery("SELECT * FROM users WHERE `Username` = :Username AND `Fqdn` = :Fqdn", array(
	                               ":Username" => $_POST['username'], ":Fqdn" => $_POST['fqdn']), 10, true);
}
catch (NotFoundException $e)
{
	throw new ResourceNotFoundException("The specified user does not exist.");
}

try
{
	$sSetting = UserSetting::CreateFromQuery("SELECT * FROM user_settings WHERE `UserId` = :UserId AND `Key` = :Key", array(
	                                         ":UserId" => $sUser->sId, ":Key" => $_POST['key']), 10, true);
}
catch (NotFoundException $e)
{
	$sSetting = new UserSetting();
	$sSetting->uKey = $_POST['key'];
	$sSetting->uUserId = $sUser->sId;
}

$sSetting->uValue = $_POST['value'];
$sSetting->uLastModified = time();
$sSetting->InsertIntoDatabase();

$sResponse = true;

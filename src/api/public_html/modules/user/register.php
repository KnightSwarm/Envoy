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

/* Validation steps for user registration:
 * - A username, FQDN, and password must be supplied and be non-empty.
 * - The user must not already exist on the given FQDN.
 * - The API user must have administrative access to the supplied FQDN. */

if(empty($_POST['username']) || empty($_POST['password']) || empty($_POST['fqdn']))
{
	$sCode = 400;
	$sError = "Missing one or more required fields.";
	return;
}

try
{
	$sExistingUser = User::CreateFromQuery("SELECT * FROM users WHERE `Username` = :Username AND `Fqdn` = :Fqdn", array(
	                                       ":Username" => $_POST['username'], ":Fqdn" => $_POST['fqdn']), 0);
	$found = true;
}
catch (NotFoundException $e)
{
	$found = false;
}

if($found === true)
{
	$sCode = 409;
	$sError = "The specified combination of username and FQDN is already in use.";
	return;
}


$sUser = new User(0);
$sUser->uUsername = $_POST['username'];
$sUser->uFqdn = $_POST['fqdn'];
$sUser->uPassword = $_POST['password'];
$sUser->uActivated = true;
$sUser->GenerateSalt();
$sUser->GenerateHash();
$sUser->InsertIntoDatabase();

$sResponse = array("user_id" => $sUser->sId);

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

class UserPermission extends CPHPDatabaseRecordClass
{
	public $table_name = "user_permissions";
	public $fill_query = "SELECT * FROM user_permissions WHERE `Id` = :Id";
	public $verify_query = "SELECT * FROM user_permissions WHERE `Id` = :Id";
	
	public $prototype = array(
		'numeric' => array(
			'UserId'		=> "UserId",
			'FqdnId'		=> "FqdnId",
			'Type'			=> "Type"
		),
		'user' => array(
			'User'			=> "UserId"
		),
		'fqdn' => array(
			'Fqdn'			=> "FqdnId"
		)
	);
	
	const SERVICE_ADMINISTRATIVE = 150;
	const ADMINISTRATIVE = 100;
	const ADMINISTRATIVE_READ = 75;
	const WRITE = 50;
	const READ = 10;
	const BANNED = 0;
}

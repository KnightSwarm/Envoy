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

class Affiliation extends CPHPDatabaseRecordClass
{
	public $table_name = "affiliations";
	public $fill_query = "SELECT * FROM affiliations WHERE `Id` = :Id";
	public $verify_query = "SELECT * FROM affiliations WHERE `Id` = :Id";
	
	public $prototype = array(
		'numeric' => array(
			'UserId' => "UserId",
			"RoomId" => "RoomId",
			"Affiliation" => "Affiliation"
		),
		'user' => array(
			'User' => "UserId",
		),
		"room" => array(
			"Room" => "RoomId"
		)
	);
	
	public const UNKNOWN = 0;
	public const OWNER = 1;
	public const ADMIN = 2;
	public const MEMBER = 3;
	public const OUTCAST = 4;
	public const NONE = 5;
}



affiliations = {
		"unknown": 0,
		"owner": 1,
		"admin": 2,
		"member": 3,
		"outcast": 4,
		"none": 5
	}

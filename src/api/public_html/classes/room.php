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

class Room extends CPHPDatabaseRecordClass
{
	public $table_name = "rooms";
	public $fill_query = "SELECT * FROM rooms WHERE `Id` = :Id";
	public $verify_query = "SELECT * FROM rooms WHERE `Id` = :Id";
	
	public $prototype = array(
		'string' => array(
			"Node"			=> "Node", /* This is the part before the @ in the JID */
			"Name"			=> "Name",
			"Description"		=> "Description"
		),
		'numeric' => array(
			"OwnerId"		=> "OwnerId",
			"FqdnId"		=> "FqdnId",
			"LastUserCount"		=> "LastUserCount"
		),
		'timestamp' => array(
			"CreationDate"		=> "CreationDate",
			"ArchivalDate"		=> "ArchivalDate"
		),
		'boolean' => array(
			"IsPrivate"		=> "IsPrivate", /* Whether the room is set to members-only */
			"IsArchived"		=> "IsArchived" /* Whether the room is set to moderated (without anyone having voice) */
		),
		'user' => array(
			"Owner"			=> "OwnerId"
		),
		"fqdn" => array(
			"Fqdn"			=> "FqdnId"
		)
	);
	
	public function __get($varname)
	{
		switch($varname)
		{
			case "uJid":
				return "{$this->uNode}@{$this->sFqdn->uFqdn}";
			default:
				return parent::__get($varname);
		}
	}
	
	public static function GetByRoomname($roomname, $expiry = 60)
	{
		return Room::CreateFromQuery("SELECT * FROM rooms WHERE `Node` = :Roomname", array("Roomname" => $roomname), $expiry, true);
	}
}

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

class User extends CPHPDatabaseRecordClass
{
	public $table_name = "users";
	public $fill_query = "SELECT * FROM users WHERE `Id` = :Id";
	public $verify_query = "SELECT * FROM users WHERE `Id` = :Id";
	
	public $prototype = array(
		'string' => array(
			'Username'		=> "Username",
			'Fqdn'			=> "Fqdn",
			'Hash'			=> "Hash",
			'Salt'			=> "Salt",
		),
		'numeric' => array(
			'FqdnId'		=> "FqdnId"
		),
		'boolean' => array(
			'Active'		=> "Active"
		),
		'fqdn' => array(
			'FqdnObject'		=> "FqdnId"
		)
	);
	
	public function CreateHash($input)
	{
		return base64_encode(pbkdf2("sha256", $input, base64_decode($this->uSalt), 30000, 32, true));
	}
	
	public function GenerateSalt()
	{
		$this->uSalt = base64_encode(mcrypt_create_iv(24, MCRYPT_DEV_URANDOM));
	}
	
	public function GenerateHash()
	{
		$this->uHash = $this->CreateHash($this->uPassword);
	}
	
	public function VerifyPassword($input)
	{
		return ($this->uHash == $this->CreateHash($input));
	}
}

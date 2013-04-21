<?php
/*
 * Envoy is more free software. It is licensed under the WTFPL, which
 * allows you to do pretty much anything with it, without having to
 * ask permission. Commercial use is allowed, and no attribution is
 * required. We do politely request that you share your modifications
 * to benefit other developers, but you are under no enforced
 * obligation to do so :)
 * 
 * Please read the accompanying LICENSE document for the full WTFPL
 * licensing text.
 */

namespace EnvoyLib;

class User extends ApiObject
{
	protected $has_lookup = true;
	
	public function __construct($username, $fqdn, $api)
	{
		$this->api = $api;
		$this->username = $username;
		$this->fqdn = $fqdn;
	}
	
	protected function FetchLookupData()
	{
		$this->lookup_data = $this->DoGetRequest("/user/lookup", array("username" => $this->username, "fqdn" => $this->fqdn));
	}
	
	protected function GetLookupVariable($varname)
	{
		switch($varname)
		{
			case "is_activated":
				return $this->lookup_data["active"];
		}
	}
	
	public static function Register($username, $fqdn, $password, $emailaddress)
	{
		
	}
	
	public function VerifyPassword($password)
	{
		
	}
}

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
	
	public static function FromUsernameFqdn($username, $fqdn, $api)
	{
		$obj = new User("{$username}@{$fqdn}", $api);
		$obj->username = $username;
		$obj->fqdn = $fqdn;
		return $obj;
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
	
	public function VerifyPassword($password)
	{
		$result = $this->DoGetRequest("/user/authenticate", array(
			"username"	=> $this->username,
			"fqdn"		=> $this->fqdn,
			"password"	=> $password
		));
		
		return $result["valid"];
	}
	
	public function GetKeypair($description)
	{
		return $this->DoGetRequest("/user/api-key", array(
			"username"	=> $this->username,
			"fqdn"		=> $this->fqdn,
			"description"	=> $description,
			"create"		=> true
		));
	}
}

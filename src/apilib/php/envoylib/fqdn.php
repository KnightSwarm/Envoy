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

class Fqdn extends ApiObject
{
	protected $has_lookup = true;
	
	public static function FromFqdn($fqdn, $api, $id=null)
	{
		$obj = new Fqdn($fqdn, $api);
		$obj->fqdn = $fqdn;
		if(!is_null($id))
		{
			$obj->id = $id;
		}
		return $obj;
	}
	
	protected function FetchLookupData()
	{
		$this->lookup_data = $this->DoGetRequest("/fqdn/lookup", array("fqdn" => $this->fqdn));
	}
	
	protected function GetLookupVariable($varname)
	{
		switch($varname)
		{
			case "name":
				return $this->lookup_data["name"];
			case "description":
				return $this->lookup_data["description"];
			case "owner_id":
				return $this->lookup_data["owner"]["id"];
			case "owner_username":
				return $this->lookup_data["owner"]["username"];
		}
	}
	
	public function ListRooms()
	{
		$room_list = $this->DoGetRequest("/room", array("fqdn" => $this->fqdn));
		return $this->ReturnAsObjects($room_list, "\EnvoyLib\Room"); /* Really, PHP? I need to specify the namespace? REALLY? */
	}
}

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

class Room extends ApiObject
{
	protected $has_lookup = true;
	
	public static function FromRoomnameFqdn($roomname, $fqdn, $api)
	{
		$obj = new Room("{$roomname}@{$fqdn}", $api);
		$obj->roomname = $roomname;
		$obj->fqdn = $fqdn;
		return $obj;
	}
	
	protected function FetchLookupData()
	{
		$this->lookup_data = $this->DoGetRequest("/room/lookup", array("roomname" => $this->roomname, "fqdn" => $this->fqdn));
	}
	
	protected function GetLookupVariable($varname)
	{
		switch($varname)
		{
			case "is_private":
				return $this->lookup_data["private"];
			case "is_archived":
				return $this->lookup_data["archived"];
			case "creation_date":
				return $this->lookup_data["creationdate"];
			case "archival_date":
				return $this->lookup_data["archivaldate"];
			case "friendly_name":
				return $this->lookup_data["friendlyname"];
			case "owner_id":
				return $this->lookup_data["owner"]["id"];
			case "owner_username":
				return $this->lookup_data["owner"]["username"];
			case "owner_name":
				return $this->lookup_data["owner"]["name"];
			case "owner_jid":
				list($roomname, $fqdn) = explode("@", $this->lookup_data["jid"], 2);
				return $this->lookup_data["owner"]["username"] . "@" . $fqdn;
			default: /* Just return the similarly named entry in the lookup data... */
				if(isset($this->lookup_data[$varname]))
				{
					return $this->lookup_data[$varname];
				}
		}
	}
}

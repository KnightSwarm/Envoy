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

class Affiliation extends ApiObject
{
	protected $has_lookup = true;
	
	public static function FromId($id, $api)
	{
		$obj = new Affiliation($id, $api);
		return $obj;
	}
	
	/* TODO: FromUserRoom function! Perhaps define that in the
	 * API object instead? */
	
	protected function FetchLookupData()
	{
		$this->lookup_data = $this->DoGetRequest("/affiliation/lookup", array("id" => $this->id, "fqdn" => $this->fqdn));
	}
	
	protected function GetLookupVariable($varname)
	{
		if(isset($this->lookup_data[$varname]))
		{
			return $this->lookup_data[$varname];
		}
	}
}

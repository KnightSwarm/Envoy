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

class ApiObject
{
	protected $has_lookup = false;
	protected $lookup_data = false;
	
	public function __get($varname)
	{
		if($this->has_lookup === true)
		{
			if($this->lookup_data === false)
			{
				$this->FetchLookupData();
			}
			
			return $this->GetLookupVariable($varname);
		}
	}
	
	protected function FetchLookupData()
	{
		var_dump("foo");
		$this->lookup_data = array();
	}
	
	protected function GetLookupVariable($varname)
	{
		return null;
	}
	
	protected function DoRequest($method, $path, $arguments)
	{
		return $this->api->DoRequest($method, $path, $arguments);
	}
	
	protected function DoGetRequest($path, $arguments)
	{
		return $this->DoRequest("get", $path, $arguments);
	}
	
	protected function DoPostRequest($path, $arguments)
	{
		return $this->DoRequest("post", $path, $arguments);
	}
}

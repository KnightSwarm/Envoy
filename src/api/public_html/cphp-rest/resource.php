<?php
/*
 * CPHP-REST is more free software. It is licensed under the WTFPL, which
 * allows you to do pretty much anything with it, without having to
 * ask permission. Commercial use is allowed, and no attribution is
 * required. We do politely request that you share your modifications
 * to benefit other developers, but you are under no enforced
 * obligation to do so :)
 * 
 * Please read the accompanying LICENSE document for the full WTFPL
 * licensing text.
 */

namespace \CPHP\REST;

if(!isset($_CPHP_REST)) { die("Unauthorized."); }

class ResourceType
{
	function __construct($api, $type, $config)
	{
		$this->type = $type;
		$this->config = $config;
		$this->item_methods = array();
		$this->list_methods = array();
		$this->subresource_plurals = array();
		$this->identifiers = array();
	}
	
	public function PluralizeSubresourceName($name)
	{
		if(isset($this->subresource_plurals[$name]))
		{
			return $this->subresource_plurals[$name];
		}
		else
		{
			return "{$name}s";
		}
	}
	
	function ProcessConfiguration($config)
	{
		if(isset($config["subresources"]))
		{
			foreach($config["subresources"] as $name => $data)
			{
				$type = $data["type"];
				
				$this->types[$name] = $type;
				
				if(isset($data["plural"]))
				{
					$this->subresource_plurals[$name] = $data["plural"];
				}
				
				if(empty($data["identifier"]))
				{
					$identifier = $this->api->default_identifiers[$type];
				}
				else
				{
					$identifier = $data["identifier"];
				}
				
				$this->identifiers[$name] = $identifier;
				
				/* Build method lookup table. */
				$this->item_methods[$this->api->Capitalize($name)] = $type;
				$this->list_methods["List" . $this->api->Capitalize($this->PluralizeSubresourceName($name))] = $type;
			}
		}
	}
	
	public function PopulateData($data)
	{
		$this->data = $data;
		
		foreach($data as $attribute => $value)
		{
			/* FIXME: Won't this break __set? Perhaps just provide dynamically
			 * using __get instead... */
			$this->$attribute = $value;
		}
	}
	
	public function __call($method, $arguments)
	{
		if(isset($this->item_methods[$method]))
		{
			/* Retrieve a single resource. */
			if(count($arguments) < 1)
			{
				/* New object... */
				$obj = $this->api->BlankResource($type);
				/* FIXME: Set own identifier as reference in new object */
				return $obj;
			}
			else
			{
				/* FIXME: Move this to root of function for both Resource and API? */
				$name = $this->item_methods[$method];
				$type = $this->types$name];
				
				$filters = array();
				$filters[$this->identifiers[$name]] = $arguments[0];
				$filters[$this->config["subresources"][$name]["field"]] = $this->primary_key;
				
				return $this->api->ObtainResource($type, $filters);
			}
		}
		elseif(isset($this->list_methods[$method]))
		{
			/* Retrieve an (optionally filtered) list of resources. */
			$type = $this->list_methods[$method];
			$filters = (count($arguments) >= 1) ? $arguments[0] : array();
			return $this->ObtainResourceList($type, $filters);
		}
	}
}

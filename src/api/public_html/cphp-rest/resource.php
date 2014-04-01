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

namespace CPHP\REST;

if(!isset($_CPHP_REST)) { die("Unauthorized."); }

class Resource
{
	function __construct($api, $type, $config)
	{
		$this->api = $api;
		$this->type = $type;
		$this->config = $config;
		$this->item_methods = array();
		$this->list_methods = array();
		$this->subresource_plurals = array();
		$this->identifiers = array();
		$this->types = array();
		$this->chain = array();
		
		$this->ProcessConfiguration($config);
	}
	
	public function PluralizeSubresourceName($name)
	{
		/* TODO: Is this necessary? */
		return $this->subresource_plurals[$name];
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
				else
				{
					$this->subresource_plurals[$name] = "{$name}s";
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
			//$this->$attribute = $value;
		}
	}
	
	public function __call($method, $arguments)
	{
		/* FIXME: All this should be merged to a common base for both API and Resource. */
		
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
				$name = $this->item_methods[$method];
				$type = $this->types[$name];
				
				return $this->api->ResolveResource($type, $arguments[0], $this);
			}
		}
		elseif(isset($this->list_methods[$method]))
		{
			/* Retrieve an (optionally filtered) list of resources. */
			$type = $this->list_methods[$method];
			$filters = (count($arguments) >= 1) ? $arguments[0] : array();
			$resources = $this->api->ResolveResource($this->PluralizeSubresourceName($type), null, $this, false, $filters);
			$new_chain = array_merge($this->chain, array($this));
			
			foreach($resources as $resource)
			{
				$resource->chain = $new_chain;
			}
			
			return $resources;
		}
	}
	
	public function __get($key)
	{
		if(array_key_exists($key, $this->config["attributes"]))
		{
			$type = $this->config["attributes"][$key]["type"];
			
			switch($type)
			{
				case "string":
				case "numeric":
				case "timestamp":
				case "custom":
					return $this->data[$key];
					break;
				default:
					/* This is a resource identifier; we need to lazy-load the resource. 
					 * A special _primary_key flag is used for this; in some cases, the
					 * root resource identifier may differ from the primary key (as it is
					 * used in this reference). We will always want to identify referenced
					 * resources by their primary key, rather than by their regular root
					 * identifier. */
					return $this->api->ResolveResource($type, $this->data[$key], null, true);
			}
		}
		return $this->data[$key];
	}
}

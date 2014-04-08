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

class Resource extends ResourceBase
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
		$this->custom_item_handlers = array();
		
		$this->ProcessConfiguration($config);
	}
	
	public function PluralizeSubresourceName($name)
	{
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
				
				if(!empty($data["item_handlers"]))
				{
					foreach($data["item_handlers"] as $handler_name => $handler_method)
					{
						$this->custom_item_handlers[$this->api->Capitalize($handler_name)] = $handler_method;
					}
				}
				
				/* Build method lookup table. We set the subresource name rather than the
				 * root resource name, as the subresource name is what the rest of the code
				 * uses internally. */
				$this->item_methods[$this->api->Capitalize($name)] = $name;
				$this->list_methods["List" . $this->api->Capitalize($this->PluralizeSubresourceName($name))] = $name;
			}
		}
	}
	
	public function PopulateData($data)
	{
		$this->data = $data;
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

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
	public $api;
	public $type;
	public $config;
	public $item_methods = array();
	public $_lazy_load = false;
	public $_api_id;
	public $_new;
	public $parent_resource;
	public $_primary_key;
	public $_original_identifier_field;
	public $_original_identifier_value;
	public $serialized;
	public $list_methods = array();
	public $subresource_plurals = array();
	public $identifiers = array();
	public $types = array();
	public $chain = array();
	public $custom_item_handlers = array();
	public $capitalized_item_handlers = array();
	public $data = array();
	public $_commit_buffer = array();
	
	
	function __construct($api, $type, $config)
	{
		$this->api = $api;
		$this->type = $type;
		$this->config = $config;
		
		$this->ProcessConfiguration($config);
	}
	
	public function Pluralize($type)
	{
		return $this->PluralizeSubresourceName($type);
	}
	
	public function PluralizeSubresourceName($name)
	{
		return $this->subresource_plurals[$name];
	}
	
	public function Singularize($type)
	{
		return $this->SingularizeSubresourceName($type);
	}
	
	public function SingularizeSubresourceName($name)
	{
		$result = array_search($name, $this->subresource_plurals);
		
		if($result !== false)
		{
			return $result;
		}
		else
		{
			throw new \Exception("No singular version of '{$name}' found.");
		}
	}
	
	public function GetRealSubresourceType($subresource_type)
	{
		if(array_key_exists($subresource_type, $this->config["subresources"]))
		{
			return $this->config["subresources"][$subresource_type]["type"];
		}
		else
		{
			throw new \Exception("No such subresource type.");
		}
	}
	
	public function GetPrimaryIdField()
	{
		return $this->api->config["resources"][$this->type]["primary_key"];
	}
	
	public function GetPrimaryId()
	{
		$primary_key_field = $this->GetPrimaryIdField();
		return $this->$primary_key_field;
	}
	
	public function SetPrimaryId($value)
	{
		$primary_key_field = $this->GetPrimaryIdField();
		$this->$primary_key_field = $value;;
	}
	
	public function ProcessConfiguration($config)
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
				
				/* Build method lookup table. We set the subresource name rather than the
				 * root resource name, as the subresource name is what the rest of the code
				 * uses internally. */
				$this->item_methods[$this->api->Capitalize($name)] = $name;
				$this->list_methods["List" . $this->api->Capitalize($this->PluralizeSubresourceName($name))] = $name;
			}
		}
		
		if(!empty($config["item_handlers"]))
		{
			foreach($config["item_handlers"] as $handler_name => $options)
			{
				$capitalized = $this->api->Capitalize($handler_name);
				$this->custom_item_handlers[$handler_name] = $options;
				$this->capitalized_item_handlers[$capitalized] = $handler_name;
			}
		}
	}
	
	public function PopulateData($data, $overwrite = false)
	{
		if($overwrite === true)
		{
			$this->data = $data;
		}
		else
		{
			$this->data = array_merge($this->data, $data);
		}
	}
	
	public function __get($key)
	{
		if(!empty($this->_lazy_load) && empty($this->data))
		{
			/* Retrieve the data for this resource first. */
			$response = $this->api->Execute($this);
			$this->PopulateData($this->api->SerializedToAttributes($this->type, $response));
		}
		
		if(array_key_exists($key, $this->config["attributes"]))
		{
			$type = $this->config["attributes"][$key]["type"];
			
			switch($type)
			{
				case "string":
				case "numeric":
				case "timestamp":
				case "boolean":
				case "custom":
					return $this->data[$key];
					break;
				default:
					if(array_key_exists($type, $this->api->config["enums"]))
					{
						/* This is an enum value of some sort. */
						return $this->data[$key];
					}
					else
					{
						/* This is a resource identifier; we need to lazy-load the resource. 
						 * A special _primary_key flag is used for this; in some cases, the
						 * root resource identifier may differ from the primary key (as it is
						 * used in this reference). We will always want to identify referenced
						 * resources by their primary key, rather than by their regular root
						 * identifier. */
						return $this->api->ResolveResource($type, $this->data[$key], null, true);
					}
			}
		}
	}
	
	public function __set($key, $value)
	{
		$this->_commit_buffer[$key] = $value;
	}
	
	public function DoCommit()
	{
		$this->api->Commit($this);
	}
	
	public function DoDelete()
	{
		$this->api->Delete($this);
	}
}

class Response extends ResourceBase
{
	/* Because resource-related functions are all expected to return
	 * something resembling a resource or list of resources - that is,
	 * an object with a 'serialized' attribute - we will have to wrap all
	 * non-resource responses for custom handlers into an object
	 * that *pretends* to be a resource. This wrapper should only be
	 * used if the custom handler does not return a Resource object. */
	 
	public function __construct($data)
	{
		$this->serialized = $data;
	}
}

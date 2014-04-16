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

require("api.php");
require("api-server.php");
require("api-client.php");
require("resource.php");
require("handler.php");
require("listrequest.php");

class ResourceBase
{
	public function __call($method, $arguments)
	{
		if(get_class($this) == "CPHP\REST\Resource")
		{
			$last = $this;
			$is_resource = true;
		}
		else
		{
			$last = null;
			$is_resource = false;
		}
		
		if($is_resource && isset($this->capitalized_item_handlers[$method]))
		{
			$handler_name = $this->capitalized_item_handlers[$method];
			$handler_obj = new Handler($this->api, $this, $handler_name, $arguments[0]);
			$handler_obj->chain = array_merge($this->chain, array($this));
			return $this->api->Execute($handler_obj); /* Immediately execute the call. */
		}
		elseif(isset($this->item_methods[$method]))
		{
			/* Retrieve a single resource. */
			$type = $this->item_methods[$method];
			
			if(count($arguments) < 1)
			{
				if($is_resource)
				{
					$real_type = $this->GetRealSubresourceType($type);
				}
				else
				{
					$real_type = $type;
				}
				
				/* New object... */
				$obj = $this->api->BlankResource($real_type);
				$obj->_new = true;
				$obj->_subresource_name = $type;
				
				if($is_resource)
				{
					$obj->parent_resource = $this;
					$obj->chain = $this->chain;
					$obj->chain[] = $this;
				}
				
				if(get_class($this->api) == "CPHP\REST\APIServer")
				{
					/* We need to manually set the implicit reference here,
					 * as there is no URL to derive it from later on. */
					if($is_resource)
					{	
						$ref_key = $this->config["subresources"][$type]["filter"];
						$ref_value =  $this->GetPrimaryId();
						$obj->$ref_key = $ref_value;
					}
				}
				
				return $obj;
			}
			else
			{
				if($is_resource)
				{
					/* A subresource is requested, so we will need to look up the actual type
					 * name - the resource type specified is just the subresource type.
					 * FIXME: This currently breaks, because the conversion would happen
					 * twice in different places. Commented out for now. */
					//$type = $this->_types[$type];
				}
				
				$obj = $this->api->ResolveResource($type, $arguments[0], $last);
				$obj->_subresource_name = $type;
				return $obj;
			}
		}
		elseif(isset($this->list_methods[$method]))
		{
			/* Retrieve an (optionally filtered) list of resources. */
			$type = $this->list_methods[$method];
			$filters = (count($arguments) >= 1) ? $arguments[0] : array();
			$bypass_auth = (count($arguments) >= 2) ? $arguments[1] : false;
			$expiry = (count($arguments) >= 3) ? $arguments[2] : 60;
			$plural = $this->Pluralize($type);
			
			$resources = $this->api->ResolveResource($plural, null, $last, false, $filters, $bypass_auth, $expiry);
			
			if($is_resource)
			{
				$current_chain = (isset($this->chain)) ? $this->chain : array();
				$new_chain = array_merge($current_chain, array($this));
				
				foreach($resources as $resource)
				{
					$resource->chain = $new_chain;
					$resource->_subresource_name = $type;
				}
			}
			
			return $resources;
		}
		else
		{
			trigger_error('Call to undefined method '.__CLASS__.'::'.$method.'()', E_USER_ERROR);
			return;
		}
	}
}

class ApiException extends \Exception
{
	protected $api_message = "";
	
	public function __construct($message = "", $code = 0, $previous = null, $api_message = "")
	{
		$this->api_message = $api_message;
		
		parent::__construct($message, $code, $previous);
	}
	
	public function GetApiMessage()
	{
		return $this->api_message;
	}
} 

class NotFoundException extends ApiException {}
class BadDataException extends ApiException {}
class NotAuthorizedException extends ApiException {}
class NotAuthenticatedException extends ApiException {}
class UnknownException extends ApiException {}
class AlreadyExistsException extends ApiException {}
class InvalidArgumentException extends ApiException {}
class MalformedRequestException extends ApiException {}
class ConfigurationException extends ApiException {}

class NonceException extends \Exception {};
class HookException extends \Exception {};

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
require("resource.php");

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
		
		if(isset($this->item_methods[$method]))
		{
			/* Retrieve a single resource. */
			if(count($arguments) < 1)
			{
				/* New object... */
				$obj = $this->api->BlankResource($type);
				
				if($is_resource)
				{
					/* FIXME: Set own identifier as reference in new object */
				}
				
				return $obj;
			}
			else
			{
				$type = $this->item_methods[$method];
				
				if($is_resource)
				{
					/* A subresource is requested, so we will need to look up the actual type
					 * name - the resource type specified is just the subresource type. */
					$type = $this->types[$name];
				}
				
				return $this->api->ResolveResource($type, $arguments[0], $last);
			}
		}
		elseif(isset($this->list_methods[$method]))
		{
			/* Retrieve an (optionally filtered) list of resources. */
			$type = $this->list_methods[$method];
			$filters = (count($arguments) >= 1) ? $arguments[0] : array();
			$resources = $this->api->ResolveResource($this->PluralizeSubresourceName($type), null, $last, false, $filters);
			
			if($is_resource)
			{
				$current_chain = (isset($this->chain)) ? $this->chain : array();
				$new_chain = array_merge($current_chain, array($this));
				
				foreach($resources as $resource)
				{
					$resource->chain = $new_chain;
				}
			}
			
			return $resources;
		}
	}
}

class NotFoundException extends \Exception {};
class NotAuthorizedException extends \Exception {};
class NotAuthenticatedException extends \Exception {};
class MalformedRequestException extends \Exception {};
class ConfigurationException extends \Exception {};
class NonceException extends \Exception {};
class HookException extends \Exception {};

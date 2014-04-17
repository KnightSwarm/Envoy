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

class APIClient extends API
{
	public function __construct($endpoint)
	{
		$this->endpoint = $endpoint;
		$this->request_cache = array();
		parent::__construct();
	}
	
	public function Authenticate($api_id, $api_key)
	{
		$this->api_id = $api_id;
		$this->api_key = $api_key;
	}
	
	public function BuildUrl($object)
	{
		/* FIXME: List URLs... */
		$components = array();
		$last = null;
		
		foreach($object->chain as $item)
		{
			$components[] = $this->GenerateUrlComponent($item, $last);
			$last = $item;
		}
		
		$components[] = $this->GenerateUrlComponent($object, $last);
		
		return implode("/", $components);
	}
	
	public function GenerateUrlComponent($object, $last)
	{
		if(get_class($object) === "CPHP\REST\Resource")
		{
			if(!empty($object->_api_id))
			{
				$id = rawurlencode($object->_api_id);
			}
			else
			{
				if($last !== null)
				{
					/* Subresource. */
					if(isset($last->config["subresources"][$object->_subresource_name]["identifier"]))
					{
						$id_field = $last->config["subresources"][$object->_subresource_name]["identifier"];
					}
					else
					{
						$id_field = $this->config["resources"][$object->_type]["identifier"];
					}
				}
				else
				{
					/* Top-level resource. */
					$id_field = $this->config["resources"][$object->_type]["identifier"];
				}
				
				$id = rawurlencode($object->$id_field);
			}
			
			$type_name = isset($object->subresource_type_name) ? $object->subresource_type_name : $object->_type;
			
			if($last !== null)
			{
				$plural = rawurlencode($last->Pluralize($type_name));
			}
			else
			{
				$plural = rawurlencode($this->Pluralize($type_name));
			}
			
			return "{$plural}/{$id}";
		}
		elseif(get_class($object) === "CPHP\REST\Handler")
		{
			return $object->handler_name;
		}
		elseif(get_class($object) === "CPHP\REST\ListRequest")
		{
			if($last !== null)
			{
				$plural = rawurlencode($last->Pluralize($object->_type));
			}
			else
			{
				$plural = rawurlencode($this->Pluralize($object->_type));
			}
			
			return $plural;
		}
	}
	
	public function ObtainResourceList($type, $filters, $chain = array(), $bypass_auth = false, $expiry = 60)
	{
		$list = new ListRequest($this, $type, $filters);
		$list->chain = $chain;
		return $this->Execute($list);
	}
	
	public function ObtainResource($type, $filters, $id, $primary_key = false, $chain = array(), $bypass_auth = false, $existing_resource = null, $expiry = 60)
	{
		$obj = $this->api->BlankResource($type);
		$obj->_lazy_load = true;
		$obj->_api_id = $id;
		$obj->_primary_key = $primary_key;
		return $obj;
	}
	
	public function Execute($object)
	{
		$path = $this->BuildUrl($object);
		
		if(get_class($object) == "CPHP\REST\Handler")
		{
			$handler_config = $object->object->config["item_handlers"][$object->handler_name];
			$method = $handler_config["method"];
			$response = $this->DoRequest($method, $path, $object->parameters);
			
			if($handler_config["response"] == "json")
			{
				/* Response was opaque JSON; just return it as is. */
				return $response;
			}
			elseif($handler_config["response"] == "resource")
			{
				/* Create new resource and populate data. */
				$resource = $this->api->BlankResource($handler_config["type"]);
				$resource->PopulateData($this->api->SerializedToAttributes($handler_config["type"], $response));
				return $resource;
			}
			elseif($handler_config["response"] = "list")
			{
				/* Create new list of resources and populate data. */
				$resources = array();
				
				foreach($response as $item)
				{
					$resource = $this->api->BlankResource($handler_config["type"]);
					$resource->PopulateData($this->api->SerializedToAttributes($handler_config["type"], $response));
					$resources[] = $resource;
				}
				
				return $resources;
			}
			else
			{
				throw new ConfigurationException("No valid expected response type configured for custom '{$object->handler_name}' handler on '{$object->object->_type}' type.");
			}
		}
		elseif(get_class($object) == "CPHP\REST\Resource")
		{
			/* Fetch the data for the resource. */
			$method = "GET";
			
			if(!empty($object->_primary_key))
			{
				$parameters = array("_primary_key" => "true");
			}
			else
			{
				$parameters = array();
			}
			
			$response = $this->DoRequest($method, $path, $parameters);
			
			/* When this method is called, we already have an object that
			 * we're lazy-loading for. Just return the serialized data, instead
			 * of an object. The object will take care of populating that data. */
			return $response;
		}
		elseif(get_class($object) == "CPHP\REST\ListRequest")
		{
			/* Fetch a list of resources... */
			$method = "GET";
			$response = $this->DoRequest($method, $path, $object->filters);
			
			$resources = array();
			
			foreach($response as $item)
			{
				$resource = $this->api->BlankResource($object->_type);
				$resource->PopulateData($this->api->SerializedToAttributes($object->_type, $item));
				$resources[] = $resource;
			}
			
			return $resources;
		}
	}
	
	public function Commit($object)
	{
		if(!empty($object->_new))
		{
			/* Create new object. We'll create a mock ListRequest for
			 * the sake of building a URL to POST the object to. */
			$list = new ListRequest($this->api, $object->_type, array());
			
			if(!empty($object->chain))
			{
				$list->chain = $object->chain;
			}
			
			$target_path = $this->BuildUrl($list);
			$new_url = $this->DoRequest("POST", $target_path, $this->AttributesToSerialized($object, $object->_commit_buffer, true));
			
			list($plural_type, $new_id) = explode("/", substr($new_url, 1));
			
			$object->SetPrimaryId($new_id);
			$object->_new = false;
			
			$object->PopulateData($object->_commit_buffer);
			$object->_commit_buffer = array();
		}
		else
		{
			/* Update existing object. */
			$target_path = $this->BuildUrl($object);
			$new_data = $this->DoRequest("POST", $target_path, $this->AttributesToSerialized($object, $object->_commit_buffer, true));
			
			$object->PopulateData($this->SerializedToAttributes($object->_type, $new_data));
		}
		
		/* Empty the commit buffer. */
		$object->_commit_buffer = array();
	}
	
	public function Delete($object)
	{
		$target_path = $this->BuildUrl($object);
		$this->DoRequest("DELETE", $target_path);
	}
	
	public function DoRequest($method, $path, $parameters = array(), $cache = true)
	{
		if(!is_array($parameters))
		{
			throw new \Exception("Parameters must be an (associative) array.");
		}
		
		if(!starts_with($path, "/"))
		{
			$path = "/" . $path;
		}
		
		if($cache === true && strtolower($method) === "get" && array_key_exists($path, $this->request_cache))
		{
			/* This is just a short-lived cache for the same resource reference
			 * appearing multiple times in the same pageload. */
			return $this->request_cache[$path];
		}
		
		/* Start request signing code */
		$get_data = (strtolower($method) == "get") ? $parameters : array();
		$post_data = (strtolower($method) == "post") ? $parameters : array();
		$nonce = random_string(16);
		$expiry = time() + $this->expiry;
		
		$signature = $this->Sign($this->api_key, $method, $path, $get_data, $post_data, $nonce, $expiry);
		/* End request signing code */
		
		if(isset($this->logger)) { $this->logger->addDebug("Request", array("method" => $method, "path" => $path, "post_data" => $post_data, "get_data" => $get_data, "signature" => $signature)); }
		
		if(strtolower($method) == "get" && !empty($parameters))
		{
			$fields = array();
			
			foreach($parameters as $key => $value)
			{
				$fields[] = rawurlencode($key) . "=" . rawurlencode($value);
			}
			
			$full_path = $path . "?" . implode("&", $fields);
		}
		else
		{
			$full_path = $path;
		}
		
		$url = $this->endpoint . $full_path;
		$curl = curl_init();
		
		curl_setopt_array($curl, array(
			CURLOPT_URL		=> $url,
			CURLOPT_HEADER => true,
			CURLOPT_RETURNTRANSFER	=> true,
			CURLOPT_USERAGENT	=> "CPHP-REST API Library/1.0",
			CURLOPT_HTTPHEADER	=> array(
				"API-Id: {$this->api_id}",
				"API-Signature: {$signature}",
				"API-Expiry: {$expiry}",
				"API-Nonce: {$nonce}",
				"Expect:" /* something something ridiculous something something */
			)
		));
		
		if(strtolower($method) == "post")
		{
			curl_setopt_array($curl, array(
				CURLOPT_POST		=> true,
				CURLOPT_POSTFIELDS	=> $parameters
			));
		}
		
		if(strtolower($method) == "delete")
		{
			curl_setopt_array($curl, array(
				CURLOPT_CUSTOMREQUEST		=> "DELETE"
			));
		}
		
		if(($result = curl_exec($curl)) !== false)
		{
			list($headerdata, $result) = explode("\r\n\r\n", $result, 2);
			
			$headers = array();
			
			foreach(explode("\n", $headerdata) as $line)
			{
				if(strpos($line, ":") === false)
				{
					continue;
				}
				
				list($key, $value) = explode(":", $line, 2);
				$value = trim($value);
				$key = strtolower($key);
				$headers[$key] = $value;
			}
			
			$json = json_decode($result, true);
			
			if(isset($this->logger)) { $this->logger->addDebug("Response", array("response" => $result)); }
			
			if(json_last_error() != JSON_ERROR_NONE)
			{
				if(isset($this->logger)) { $this->logger->addError("The response returned by the API was not valid JSON.", array("response" => $result)); }
				echo($result);
				throw new ApiException("The response returned by the API was not valid JSON.", 0, null, $result);
			}
			
			$status = curl_getinfo($curl, CURLINFO_HTTP_CODE);
			
			switch($status)
			{
				case 200:
					/* All went perfectly. */
					if($cache === true && strtolower($method) === "get")
					{
						$this->request_cache[$path] = $json;
					}
					
					return $json;
				case 201:
					/* New resource was created, URL returned as Location header. */
					return $headers["location"];
					break;
				case 400:
					/* Bad or incomplete request data was provided. */
					throw new BadDataException("The provided parameters were invalid or incomplete.", 0, null, $json["error"]);
				case 401:
					/* The client is not authenticated. */
					throw new NotAuthenticatedException("No valid API credentials were provided, or there was an STS mismatch.", 0, null, $json["error"]);
				case 403:
					/* The client is trying to access or modify a resource they are not permitted to access. */
					throw new NotAuthorizedException("The provided API credentials do not grant access to this resource or operation.", 0, null, $json["error"]);
				case 404:
					/* The specified resource does not exist. */
					throw new NotFoundException("The specified resource does not exist.", 0, null, $json["error"]);
				case 409:
					/* The client tried to create a resource that already exists. */
					throw new AlreadyExistsException("A resource with the specified identifier already exists.", 0, null, $json["error"]);
				case 422:
					/* The client tried to make a request, but (part of) the request data was invalid. */
					throw new InvalidArgumentException("One or more of the specified parameters contained invalid data.", 0, null, $json["error"]);
				default:
					throw new ApiException("An unrecognized status code ({$status}) was returned.", 0, null, $json["error"]);
			}
			
			return $json;
		}
		else
		{
			$error = curl_error($curl);
			$errno = curl_errno($curl);
			throw new UnknownException("cURL failed with error {$errno} ({$error})");
		}
	}
}

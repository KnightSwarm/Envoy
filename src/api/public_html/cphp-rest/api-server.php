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

class APIServer extends API
{
	public function ProcessRequest()
	{
		try
		{
			$this->RequireAuthentication();
			
			/* Discard the leading slash */
			$path = substr(trim($_SERVER['REQUEST_URI']), 1);
			
			if(strpos($path, "?") !== false)
			{
				list($path, $bogus) = explode("?", $path, 2);
			}
			
			$segments = explode("/", $path);
			$queries = array_chunk($segments, 2);
			$last = null;
			$chain = array();
			
			$primary_key = !empty($_GET["_primary_key"]);
			
			$filters = array();
			
			foreach($_GET as $key => $value)
			{
				if(substr($key, 0, 1) !== "_") /* Ignore reserved keys; those are not filters. */
				{
					$filters[$key] = $value;
				}
			}
			
			foreach($queries as $query)
			{	
				if(count($query) == 2)
				{
					$result = $this->ResolveResource($query[0], $query[1], $last, $primary_key);
					$last = $result;
				}
				elseif(count($query) == 1)
				{
					try
					{
						$result = $this->ResolveResource($query[0], null, $last, $primary_key, $filters);
					}
					catch (NotFoundException $e)
					{
						if($last !== null && array_key_exists($query[0], $last->custom_item_handlers))
						{
							//$response = $last->custom_item_handlers[$query[0]]($last);
							$response = $this->registered_item_handlers[$last->type][$query[0]]($last);
							
							if(!is_object($response) || get_class($response) !== "\CPHP\REST\Resource")
							{
								/* Perhaps this is an array of Resources? */
								if(is_array($response))
								{
									$new_responses = array();
									
									foreach($response as $response_key => $response_item)
									{
										if(!is_object($response_item) || get_class($response_item) !== "\CPHP\REST\Resource")
										{
											/* Wrap anything that isn't a Resource into a Response shim. */
											$new_responses[$response_key] = new Response($response_item);
										}
										else
										{
											$new_responses[$response_key] = $response_item;
										}
									}
									
									$response = $new_responses;
								}
								else
								{
									/* We got some sort of other serializable data back - we'll
									 * have to wrap this into a Response shim, so as to not
									 * upset the rest of the code. */
									$response = new Response($response);
								}
							}
							
							$result = $response;
						}
						else
						{
							throw new NotFoundException("Resource type for '{$query[0]}' not found, and no custom handlers available with this name.", 0, $e);
						}
					}
				}
				else
				{
					/* This should never happen!
					 * FIXME: Logging. */
				}
			}
			
			echo($this->SerializeResults($result));
		}
		catch (NotFoundException $e)
		{
			http_status_code(404);
			echo(json_encode(array("error" => $e->getMessage())));
		}
		catch (NotAuthorizedException $e)
		{
			http_status_code(403);
			echo(json_encode(array("error" => $e->getMessage())));
		}
		catch (NotAuthenticatedException $e)
		{
			header('WWW-Authenticate: APIKey realm="API"');
			http_status_code(401);
			echo(json_encode(array("error" => $e->getMessage())));
		}
		catch (MalformedRequestException $e)
		{
			http_status_code(422);
			echo(json_encode(array("error" => $e->getMessage())));
		}
		catch (\Exception $e)
		{
			switch(strtolower(ini_get('display_errors')))
			{
				case "1":
				case "on":
				case "true":
					throw $e; /* Let CPHP handle it. */
					break;
				default:
					/* This is really just to be able to present a JSON-formatted error. */
					$exception_class = get_class($e);
					$exception_message = $e->getMessage();
					$exception_file = $e->getFile();
					$exception_line = $e->getLine();
					$exception_trace = $e->getTraceAsString();
					
					error_log("Uncaught {$exception_class} in {$exception_file}:{$exception_line} ({$exception_message}). Traceback: {$exception_trace}");
					
					http_status_code(500);
					echo(json_encode(array("error" => "An unexpected error occurred. This error has been logged.")));
					die();
					break;
			}
		}
	}
	
	public function RequireAuthentication()
	{
		/* TODO: Will have to reflow this code when more authentication
		 * methods are implemented. */
		if(array_key_exists("keypair", $this->config["authentication_methods"]))
		{
			if(empty($_SERVER['HTTP_API_EXPIRY']))
			{
				throw new MalformedRequestException("No expiry timestamp was specified in the request.");
			}
			
			if(empty($_SERVER['HTTP_API_NONCE']))
			{
				throw new MalformedRequestException("No nonce was specified in the request.");
			}
			
			$keypair_config = $this->config["authentication_methods"]["keypair"];
			$key_field = $keypair_config["key_field"];
			
			if(empty($_SERVER['HTTP_API_ID']) || empty($_SERVER['HTTP_API_SIGNATURE']))
			{
				throw new NotAuthenticatedException("You did not provide a valid API key ID and signature.");
			}
			
			$filters = array();
			$filters[$keypair_config["id_field"]] = $_SERVER["HTTP_API_ID"];
			
			try
			{
				$keypair = $this->ObtainResource($keypair_config["resource"], $filters);
			}
			catch (NotFoundException $e)
			{
				throw new NotAuthenticatedException("The API key you specified is invalid.");
			}
			
			$signature = $_SERVER['HTTP_API_SIGNATURE'];
			$signing_key = $keypair->$key_field;
			$verb = $_SERVER["REQUEST_METHOD"];
			$uri = $_SERVER["REQUEST_URI"];
			$nonce = $_SERVER['HTTP_API_NONCE'];
			$expiry = $_SERVER['HTTP_API_EXPIRY'];
			
			$signature_correct = $this->VerifySignature($signature, $signing_key, $verb, $uri, $_GET, $_POST, $nonce, $expiry);
			
			if($signature_correct !== true)
			{
				throw new NotAuthenticatedException("The request signature was invalid.");
			}
			
			if(time() > (int) $expiry)
			{
				throw new NotAuthenticatedException("The request has expired.");
			}
			
			try
			{
				$this->RegisterNonce($_SERVER["HTTP_API_ID"], $nonce);
			}
			catch (NonceException $e)
			{
				throw new NotAuthenticatedException("The specified nonce has been used before.");
			}
		}
	}
	
	private function BuildQuery($type, $filters, $single = false)
	{
		if(!is_array($filters))
		{
			throw new \Exception("The 'filters' argument was not an array.");
		}
		
		$map = $this->config["resources"][$type]["attributes"];
		$predicates = array();
		$values = array();
		$table = $this->config["resources"][$type]["table"];
		
		foreach($filters as $attribute => $value)
		{
			if(!array_key_exists($attribute, $map))
			{
				continue; /* This is not a valid filter attribute. */
				/* TODO: Logging! */
			}
			
			$attribute_type = $map[$attribute]["type"];
			
			if($attribute_type == "custom")
			{
				if(array_key_exists($type, $this->custom_decoder) && array_key_exists($attribute, $this->custom_decoder[$type]))
				{
					$function_name = $this->custom_decoder[$type][$attribute];
				}
				else
				{
					throw new ConfigurationException("Custom decoder function expected, but not registered for '{$attribute}' attribute on '{$type}' resource.");
				}
				
				$decoded_filters = $function_name($this, $value, $filters);
				
				foreach($decoded_filters as $sub_attribute => $sub_value)
				{
					$field = $map[$sub_attribute]["field"];
					
					/* Don't let the custom decoder override a normally-set filter */
					if(!isset($values[$field]))
					{						
						$predicates[] = "{$field} = :{$field}";
						$values[$field] = $sub_value;
					}
				}
			}
			else
			{
				$field = $map[$attribute]["field"];
				$predicates[] = "{$field} = :{$field}";
				
				if(array_key_exists("enums", $this->config) && array_key_exists($attribute_type, $this->config["enums"]))
				{
					if(array_key_exists($value, $this->config["enums"][$attribute_type]))
					{
						$values[$field] = $this->config["enums"][$attribute_type][$value];
					}
					else
					{
						throw new ConfigurationException("Found enum value '{$data[$field]}' for type '{$attribute_type}', which is not specified in the API configuration!");
					}
				}
				else
				{
					$values[$field] = $value;
				}
			}
		}
		
		if(empty($predicates))
		{
			$query = "SELECT * FROM {$table}";
		}
		else
		{
			$query = "SELECT * FROM {$table} WHERE  " . implode(" AND ", $predicates);
		}
		
		 if($single === true)
		 {
			 $query .= " LIMIT 1";
		 }
		
		return array($query, $values);
	}
	
	public function ObtainResourceList($type, $filters, $chain = array())
	{
		global $database;
		list($query, $params) = $this->BuildQuery($type, $filters);
		
		if($result = $database->CachedQuery($query, $params))
		{
			$return_objects = array();
			
			foreach($result->data as $row)
			{
				$data = $row;
				$resource = $this->BlankResource($type);
				$resource->serialized = $this->ResultsToSerialized($type, $data);
				$resource->PopulateData($this->SerializedToAttributes($type, $resource->serialized));
				$return_objects[] = $resource;
			}
			
			return $return_objects;
		}
		else
		{
			/* Not found... */
			throw new NotFoundException("No results for query.");
		}
	}
	
	public function ObtainResource($type, $filters, $id = null, $primary_key = false, $chain = array())
	{
		/* $filters: A single filter for a normal identifier query, or
		 * multiple filters if a subresource. */
		global $database;
		
		list($query, $params) = $this->BuildQuery($type, $filters, true);
		
		if($result = $database->CachedQuery($query, $params))
		{
			$data = $result->data[0];
			$resource = $this->BlankResource($type);
			$resource->serialized = $this->ResultsToSerialized($type, $data);
			$resource->PopulateData($this->SerializedToAttributes($type, $resource->serialized));
			return $resource;
		}
		else
		{
			/* Not found... */
			throw new NotFoundException("No results for query.");
		}
	}
	
	/* RegisterEncoder and RegisterDecoder are used to register methods
	 * that generate or parse specific attributes on a resource type that are
	 * marked as "custom". These are "context-aware"; they operate in the
	 * context of a particular kind of resources and - in the case of the 
	 * encoder - in the context of actual data held by a resource. */
	public function RegisterEncoder($type, $attribute, $function)
	{
		if(!isset($this->custom_encoder[$type]))
		{
			$this->custom_encoder[$type]  = array();
		}
		
		$this->custom_encoder[$type][$attribute] = $function;
	}
	
	public function RegisterDecoder($type, $attribute, $function)
	{
		if(!isset($this->custom_decoder[$type]))
		{
			$this->custom_decoder[$type]  = array();
		}
		
		$this->custom_decoder[$type][$attribute] = $function;
	}
	
	public function RegisterAuthenticator($name, $function)
	{
		$this->authenticator[$name] = $function;
	}
	
	public function RegisterHandler($type, $name, $function)
	{
		if(!isset($this->registered_item_handlers[$type]))
		{
			$this->registered_item_handlers[$type]  = array();
		}
		
		$this->registered_item_handlers[$type][$name] = $function;
	}
}

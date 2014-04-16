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
	public $_keypair = true;
	private $_bypass_all_auth = false;
		
	public function ProcessRequest()
	{
		global $database;
		
		try
		{
			$this->RequireAuthentication();
			
			/* Discard the leading slash */
			$path = substr(trim($_SERVER['REQUEST_URI']), 1);
			$method = strtoupper($_SERVER["REQUEST_METHOD"]);
			
			if(strpos($path, "?") !== false)
			{
				list($path, $bogus) = explode("?", $path, 2);
			}
			
			$segments = explode("/", $path);
			
			foreach($segments as $key => $value)
			{
				$segments[$key] = rawurldecode($value);
			}
			
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
			
			$last_query = end($queries);
			
			foreach($queries as $query)
			{
				if(count($query) == 2)
				{
					$result = $this->ResolveResource($query[0], $query[1], $last, $primary_key);
					
					if($query === $last_query && $method === "POST")
					{
						/* Update the object. */
						$result = $this->UpdateObject($result, $_POST);
						
						/* If successful, update $result to have an up-to-date version of the resource. 
						 * This can then be returned to the client. */
						$result = $this->ResolveResource($query[0], $query[1], $last, $primary_key);
					}
					elseif($query === $last_query && $method === "PUT")
					{
						/* Overwrite the object.
						 * FIXME: Implement this. */
						http_status_code(405);
						die();
					}
					elseif($query === $last_query && $method === "DELETE")
					{
						/* Delete the object. */
						$this->DeleteObject($result);
					}
					
					$last = $result;
				}
				elseif(count($query) == 1)
				{
					if($last !== null && array_key_exists($query[0], $last->custom_item_handlers) && $last->custom_item_handlers[$query[0]]["method"] === $method)
					{
						/* A custom handler was called. */
						if(!array_key_exists($last->_type, $this->registered_item_handlers) || !array_key_exists($query[0], $this->registered_item_handlers[$last->_type]))
						{
							throw new ConfigurationException("No custom handler function was provided for {$last->_type}/{$query[0]}, but the configuration says there should be one.");
						}
						
						$response = $this->registered_item_handlers[$last->_type][$query[0]]($this, $last);
						
						if(!is_object($response) || get_class($response) !== "CPHP\REST\Resource")
						{
							/* Perhaps this is an array of Resources? */
							if(is_array($response))
							{
								$new_responses = array();
								
								foreach($response as $response_key => $response_item)
								{
									if(!is_object($response_item) || get_class($response_item) !== "CPHP\REST\Resource")
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
						if($query === $last_query && $method === "POST")
						{
							/* Create a new object. We'll use the $last object, if it exists,
							 * as a preset value (similar to a filter for retrieval). */
							$subresource_type = $this->Singularize($query[0]);
							$new_type = $this->GetRealSubresourceType($subresource_type);
							
							$preset = array();
							
							if($last !== null)
							{	
								$ref_key = $last->config["subresources"][$subresource_type]["filter"];
								$ref_value =  $last->GetPrimaryId();
								$preset[$ref_key] = $ref_value;
							}
							
							$data = array_merge($_POST, $preset);
							$new_id = rawurlencode($this->CreateNewObject($new_type, $data, $last));
							
							$plural_type = rawurlencode($this->Pluralize($new_type));
							$url = "/{$plural_type}/{$new_id}";
							
							http_status_code(201); /* 201 Created */
							redirect($url);
						}
						else
						{
							/* Get a list of existing objects. */
							try
							{
								$result = $this->ResolveResource($query[0], null, $last, $primary_key, $filters);
							}
							catch (NotFoundException $e)
							{
								throw new NotFoundException("Resource type for '{$query[0]}' not found, and no custom handlers available with this name.", 0, $e);
							}
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
		catch (AlreadyExistsException $e)
		{
			http_status_code(409);
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
	
	public function Commit(&$object)
	{
		if(!empty($object->_new))
		{
			if(!empty($object->chain))
			{
				$last = end($object->chain);
			}
			else
			{
				$last = null;
			}
			
			$preset = array();
			
			if($last !== null)
			{
				$ref_key = $last->config["subresources"][$object->_subresource_name]["filter"];
				$ref_value =  $last->GetPrimaryId();
				$preset[$ref_key] = $ref_value;
			}
			
			$data = array_merge($object->_commit_buffer, $preset);
			$new_id = $this->CreateNewObject($object->_type, $data, $last);
			
			/* Retrieve our newly created object as a fresh resource. */
			$filters = array();
			$filters[$object->GetPrimaryIdField()] = $new_id;
			$object = $this->ObtainResource($object->_type, $filters, null, false, $object->chain, false, $object);
			//$object->data = $object->_commit_buffer;
			//$id_field = $object->GetPrimaryIdField();
			//$object->data[$id_field] = $new_id;
			//$object->serialized = $this->AttributesToSerialized($object, null, true);
			$object->_commit_buffer = array();
		}
		else
		{
			$this->UpdateObject($object, $object->_commit_buffer);
			$object->_commit_buffer= array();
		}
	}
	
	public function Delete($object)
	{
		$this->DeleteObject($object);
	}
	
	public function DeleteObject($object)
	{
		/* First check if the user is allowed to do this. */
		if($this->CallAuthenticator($this->config["resources"][$type]["authenticator"], "delete", $object, $this->_keypair) !== true)
		{
			throw new NotAuthorizedException("You are not allowed to delete this resource.");
		}
		
		$target_table = $this->config["resources"][$object->_type]["table"];
		$id_field = $object->config["attributes"][$object->GetPrimaryIdField()]["field"];
		$id_value = $object->GetPrimaryId();
		
		$db_query = "DELETE FROM {$target_table} WHERE `{$id_field}` = :{$id_field}";
		
		$parameters = array();
		$parameters[$id_field] = $id_value;
		
		$database->CachedQuery($db_query, $parameters, 0);
	}
	
	public function UpdateObject($object, $data)
	{
		global $database;
		
		$object->PopulateData($this->SerializedToAttributes($object->_type, $data, true));
		
		/* Check if the user is allowed to do this. */
		if($this->CallAuthenticator($this->config["resources"][$object->_type]["authenticator"], "update", $object, $this->_keypair) !== true)
		{
			throw new NotAuthorizedException("You are not allowed to update this resource.");
		}
		
		$parameters = $this->SerializedToQueryParameters($object->_type, $data);
		$target_table = $this->config["resources"][$object->_type]["table"];
		
		$assignments = array();
		
		foreach($parameters as $key => $value)
		{
			$assignments[] = "`{$key}` = :{$key}";
		}
		
		$assignment_string = implode(",", $assignments);
		
		$id_field = $object->config["attributes"][$object->GetPrimaryIdField()]["field"];
		$id_value = $object->GetPrimaryId();
		
		if(array_key_exists($id_field, $parameters))
		{
			throw new MalformedRequestException("You cannot modify the primary key of a resource.");
		}
		
		$parameters[$id_field] = $id_value;
		
		$db_query = "UPDATE {$target_table} SET {$assignment_string} WHERE `{$id_field}` = :{$id_field}";
		
		try
		{
			$database->CachedQuery($db_query, $parameters, 0);
		}
		catch (\DatabaseDuplicateException $e)
		{
			/* There was a key uniqueness conflict. */
			throw new AlreadyExistsException("A resource with these key(s) already exists.", 0, $e);
		}
		
		$object->serialized = $this->AttributesToSerialized($object);
	}
	
	public function CreateNewObject($type, $data, $last = null)
	{
		global $database;
		
		$obj = $this->BlankResource($type);
		$obj->_new = true;
		
		if($last !== null)
		{
			$obj->parent_resource = $last;
		}
		
		$obj->PopulateData($this->SerializedToAttributes($type, $data, true));
		
		/* Check if the user is allowed to do this. */
		if($this->CallAuthenticator($this->config["resources"][$type]["authenticator"], "create", $obj, $this->_keypair) !== true)
		{
			throw new NotAuthorizedException("You are not allowed to create this resource.");
		}
		
		$parameters = $this->SerializedToQueryParameters($type, $data);
		$target_table = $this->config["resources"][$type]["table"];
		
		$field_names = implode("`, `", array_keys($parameters));
		$value_names = implode(", :", array_keys($parameters));
		
		$query = "INSERT INTO {$target_table} (`{$field_names}`) VALUES (:{$value_names})";
		
		try
		{
			$new_id = $database->CachedQuery($query, $parameters, 0);
		}
		catch (\DatabaseDuplicateException $e)
		{
			/* There was a key uniqueness conflict. */
			throw new AlreadyExistsException("A resource with these key(s) already exists.", 0, $e);
		}
		
		return $new_id;
	}
	
	public function SerializedToQueryParameters($type, $data, $include_private = false)
	{
		$results = array();
		$handler = new \CPHPFormHandler($data, true);
		
		foreach($this->config["resources"][$type]["attributes"] as $attribute => $settings)
		{
			if($include_private !== true && !empty($settings["private"]))
			{
				continue; /* This attribute is private, and should not be included. */
			}
			
			if(!isset($data[$attribute]))
			{
				continue;
			}
			else
			{
				$value = $data[$attribute];
				
				switch($settings["type"])
				{
					case "string":
					case "boolean":
						/* Leave the value unchanged. */
						break;
					case "numeric":
						$value = $this->ParseNumeric($value);
						break;
					case "timestamp":
						$value = (int) $value;
						break;
					case "custom":
						/* We ignore these. */
						continue;
					default:
						/* Resource reference. enum or custom type.
						 * FIXME: Implement custom types. */
						if(array_key_exists($settings["type"], $this->config["enums"]))
						{
							/* This is an enum. */
							if(!array_key_exists($value, $this->config["enums"][$settings["type"]]))
							{
								throw new BadDataException("Enum value not found.");
							}
							$value = $this->config["enums"][$settings["type"]][$value];
						}
						elseif(is_object($value) && get_class($value) === "CPHP\REST\Resource")
						{
							/* This is a Resource object. Extract the ID. */
							$value = $value->GetPrimaryId();
						}
						break;
				}
			}
			
			$db_field = $settings["field"];
			$results[$db_field] = $value;
		}
		
		return $results;
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
				$keypair = $this->ObtainResource($keypair_config["resource"], $filters, null, false, array(), true);
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
			
			$this->_keypair = $keypair; /* Store the keypair for later use in authenticators. */
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
	
	public function ObtainResourceList($type, $filters, $chain = array(), $bypass_auth = false, $expiry = 60)
	{
		global $database;
		list($query, $params) = $this->BuildQuery($type, $filters);
		
		if($result = $database->CachedQuery($query, $params, $expiry))
		{
			$return_objects = array();
			
			foreach($result->data as $row)
			{
				$data = $row;
				$resource = $this->BlankResource($type);
				$resource->serialized = $this->ResultsToSerialized($type, $data);
				$resource->PopulateData($this->SerializedToAttributes($type, $this->ResultsToSerialized($type, $data, true), false, true));
				
				/* Check if the user is allowed to do this. */
				if($bypass_auth === false && $this->CallAuthenticator($this->config["resources"][$type]["authenticator"], "get", $resource, $this->_keypair) !== true)
				{
					continue; /* Don't add this one to the output, and skip to next. */
				}
				
				$return_objects[] = $resource;
			}
			
			if(count($return_objects) > 0)
			{
				return $return_objects;
			}
			else
			{
				/* None of the results passed the authenticator. Pretend nothing was
				 * found. */
				throw new NotFoundException("No results for query.");
			}
		}
		else
		{
			/* Not found... */
			throw new NotFoundException("No results for query.");
		}
	}
	
	public function ObtainResource($type, $filters, $id = null, $primary_key = false, $chain = array(), $bypass_auth = false, $existing_resource = null, $expiry = 60)
	{
		/* $filters: A single filter for a normal identifier query, or
		 * multiple filters if a subresource. */
		global $database;
		
		list($query, $params) = $this->BuildQuery($type, $filters, true);
		
		if($result = $database->CachedQuery($query, $params, $expiry))
		{
			$data = $result->data[0];
			
			if($existing_resource === null)
			{
				$resource = $this->BlankResource($type);
			}
			else
			{
				$resource = $existing_resource;
			}
			
			$resource->serialized = $this->ResultsToSerialized($type, $data);
			/* We re-serialize here, to include the private attributes. */
			$resource->PopulateData($this->SerializedToAttributes($type, $this->ResultsToSerialized($type, $data, true), false, true));
			
			/* Check if the user is allowed to do this. */
			
			if($bypass_auth === false && $this->CallAuthenticator($this->config["resources"][$type]["authenticator"], "get", $resource, $this->_keypair) !== true)
			{
				throw new NotAuthorizedException("You are not allowed to retrieve this resource.");
			}
			
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
	
	public function CallAuthenticator($name, $action, $object, $keypair)
	{
		if($keypair === true || $this->_bypass_all_auth === true)
		{
			/* This is used for pre-auth internal API calls. Once the client is
			 * authenticated, this variable will contain a keypair resource
			 * instead. */
			return true;
		}
		
		if(array_key_exists($name, $this->authenticator))
		{
			/* Authenticators can access everything. */
			$this->_bypass_all_auth = true;
			$result = $this->authenticator[$name]($this, $object, $keypair, $action);
			$this->_bypass_all_auth = false;
			return $result;
		}
		else
		{
			throw new ConfigurationException("No authenticator registered for '{$name}'.");
		}
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

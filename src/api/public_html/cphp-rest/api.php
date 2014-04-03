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

class API extends ResourceBase
{
	public function __construct()
	{
		$this->custom_encoder = array();
		$this->custom_decoder = array();
		$this->custom_type_encoder = array();
		$this->custom_type_decoder = array();
		$this->authenticator = array();
		$this->column_map = array();
		$this->resource_plurals = array();
		$this->api = $this; /* Shim to make ResourceBase functions work correctly. */
		$this->expiry = 60 * 60 * 24; /* TODO: Make this configurable. */
	}
	
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
					$result = $this->ResolveResource($query[0], null, $last, $primary_key, $filters);
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
			$nonce = $_SERVER['HTTP_API_NONCE']; /* FIXME! */
			$expiry = $_SERVER['HTTP_API_EXPIRY'];
			
			if($this->VerifySignature($signature, $signing_key, $verb, $uri, $_GET, $_POST, $nonce, $expiry) !== true)
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
	
	public function SerializeResults($results)
	{
		if(is_array($results))
		{
			$serialized = array();
			
			foreach($results as $result)
			{
				$serialized[] = $result->serialized;
			}
			
			return json_encode($serialized);
		}
		else
		{
			return json_encode($results->serialized);
		}
	}
	
	public function ResolveResource($type, $id = null, $last = null, $primary_key = false, $filters = array())
	{
		/* The $last argument holds either null (if the resource is top-level) or the
		 * object representing the resource that the requested resource is a child
		 * of. The $primary_key argument specifies whether the specified resource
		 * identifier is a primary key, rather than a regular identifier. Specify null
		 * for the $id to retrieve a list of resources, rather than a single item. */
		
		if($last === null)
		{
			/* Top-level resource. */
			if(array_key_exists($type, $this->config["resources"]))
			{
				/* This is a direct type specification. */
				$type_name = $type;
			}
			else
			{
				/* This is a plural form (as used in a URL). */
				$type_name = array_search($type, $this->resource_plurals);
				
				if($type_name === false)
				{
					throw new NotFoundException("Resource type for '{$type}' not found.");
				}
			}
			
			$resource_type = $this->config["resources"][$type_name];
		}
		else
		{
			/* Subresource. */
			
			$subresource_type_name = array_search($type, $last->subresource_plurals);
			
			if($subresource_type_name === false)
			{
				throw new NotFoundException("Resource type for '{$type}' not found.");
			}
			
			$subresource_type = $last->config["subresources"][$subresource_type_name];
			$type_name = $subresource_type["type"];
			$resource_type = $this->config["resources"][$type_name];
			
			$last_id_field = $subresource_type["filter"];
			$last_key = $last->config["primary_key"];
			$last_id_value = $last->$last_key;
			
			$filters[$last_id_field] = $last_id_value;
		}
		
		if($last === null)
		{
			$chain = array();
		}
		else
		{
			$chain = $last->chain;
			$chain[] = $last; /* Add the last item itself.. */
		}
		
		if($id !== null)
		{
			/* Specific object was requested. */
			if($primary_key === true)
			{
				$current_id_field = $resource_type["primary_key"];
			}
			else
			{
				$current_id_field = (isset($subresource_type) && isset($subresource_type["identifier"])) ? $subresource_type["identifier"] : $resource_type["identifier"];
			}
			
			$current_id_value = $id;
			
			$filters[$current_id_field] = $current_id_value;
			
			$resource = $this->ObtainResource($type_name, $filters);
			$resource->chain = $chain;
			
			$last = $resource;
			
			return $resource;
		}
		else
		{
			/* List of objects or custom handler was requested. */
			// FIXME: Custom handlers
			try
			{
				$resources = $this->ObtainResourceList($type_name, $filters);
				
				foreach($resources as $resource)
				{
					$resource->chain = $chain;
				}
				
				return $resources;
			}
			catch (NotFoundException $e)
			{
				/* No such resource exists, FIXME: check custom handlers. */
				throw $e;
			}
		}
	}
	
	public function Capitalize($name)
	{
		$capitalized_words = array();
		
		foreach(explode("_", $name) as $word)
		{
			$capitalized_words[] = ucfirst($word);
		}
		
		return implode("", $capitalized_words);
	}
	
	public function PluralizeResourceName($name)
	{
		if(isset($this->resource_plurals[$name]))
		{
			return $this->resource_plurals[$name];
		}
		else
		{
			return "{$name}s";
		}
	}
	
	public function LoadConfiguration($path)
	{
		$config = json_decode(file_get_contents($path), true);
		
		if(json_last_error() !== JSON_ERROR_NONE)
		{
			throw new ConfigurationException("The supplied configuration is not valid JSON.");
		}
		
		$this->config = $config;
		$this->item_methods = array();
		$this->list_methods = array();
		$this->default_identifiers = array();
		
		if(isset($config["resources"]))
		{
			foreach($config["resources"] as $type => $data)
			{
				$this->column_map[$type] = array();
				
				if(isset($data["plural"]))
				{
					$this->resource_plurals[$type] = $data["plural"];
				}
				else
				{
					$this->resource_plurals[$type] = "{$type}s";
				}
				
				if(empty($data["identifier"]))
				{
					throw new ConfigurationException("No identifier specified for resource type {$type}.");
				}
				
				$this->default_identifiers[$type] = $data["identifier"];
				
				/* Build method lookup table. */
				if(empty($data["private"]))
				{
					$this->item_methods[$this->Capitalize($type)] = $type;
					$this->list_methods["List" . $this->Capitalize($this->PluralizeResourceName($type))] = $type;
				}
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
	
	public function ResultsToSerialized($type, $data)
	{
		$attributes = array();
		$custom_attributes = array();
		
		foreach($this->config["resources"][$type]["attributes"] as $attribute => $settings)
		{
			if($settings["type"] == "custom")
			{
				/* Queue for later processing. */
				$custom_attributes[] = $attribute;
			}
			else
			{
				if(!isset($settings["field"]))
				{
					throw new ConfigurationException("No field name specified for non-custom attribute {$attribute} on {$type} resource.");
				}
				
				$field = $settings["field"];
				$attribute_type = $settings["type"];
				
				if($data[$field] === null)
				{
					/* Don't touch a null; leave it as it is. 
					 * FIXME: Currently no nulls are returned at all, they are replaced by empty strings. */
					$value = null;
				}
				else
				{
					switch($attribute_type)
					{
						case "string":
							$value = $data[$field];
							break;
						case "numeric":
							/* Numeric values are also returned as a string, to work around limitations in
							 * how Javascript and JSON deal with real numeric values. */
							$value = (string) $data[$field];
							break;
						case "timestamp":
							$value = (string) unix_from_mysql($data[$field]);
							break;
						case "boolean":
							/* Convert to boolean. */
							$value = ($data[$field] == 1) ? true : false;
							break;
						default:
							/* Check if the specified type is a known enum. */
							if(array_key_exists("enums", $this->config) && array_key_exists($attribute_type, $this->config["enums"]))
							{
								$value = array_search($data[$field], $this->config["enums"][$attribute_type]);
								
								if($value === false)
								{
									throw new ConfigurationException("Found enum key '{$data[$field]}' for type '{$attribute_type}', which is not specified in the API configuration!");
								}
							}
							else
							{
								/* Likely a resource type. Just return the numeric value and let the client
								 * library resolve it to a resource. Again, return as string.
								 * TODO: Check this on the server side, for error logging purposes? */
								$value = (string) $data[$field];
								break;
							}
					}
				}
				
				$attributes[$attribute] = $value;
			}
		}
		
		/* Now that we've populated the basic-typed attributes, allow for
		 * custom-generated attributes to be processed with access to
		 * basic-typed values. We'll provide a temporary 'mock' resource
		 * that the custom encoder functions can operate on, in a read-only
		 * fashion. */
		$mock_resource = $this->BlankResource($type);
		$mock_resource->serialized = $attributes;
		$mock_resource->PopulateData($this->SerializedToAttributes($type, $mock_resource->serialized, true));
		 
		foreach($custom_attributes as $attribute)
		{
			if(array_key_exists($type, $this->custom_encoder) && array_key_exists($attribute, $this->custom_encoder[$type]))
			{
				$function_name = $this->custom_encoder[$type][$attribute];
			}
			else
			{
				throw new ConfigurationException("Custom encoder function expected, but not registered for '{$attribute}' attribute on '{$type}' resource.");
			}
			
			try
			{
				$attributes[$attribute] = $function_name($this, $mock_resource);
			}
			catch (\Exception $e)
			{
				$exception_type = get_class($e);
				$message = $e->getMessage();
				throw new HookException("A {$exception_type} exception occurred within a custom encoder hook: {$message}", 0, $e);
			}
		}
		
		return $attributes;
	}
	
	public function SerializedToAttributes($type, $data, $ignore_missing = false)
	{
		/* $ignore_missing is used for the creation of mock resource objects, where
		 * not all data is available yet. */
		$attributes = array();
		
		foreach($this->config["resources"][$type]["attributes"] as $attribute => $settings)
		{
			if(!array_key_exists($attribute, $data))
			{
				if($ignore_missing === false)
				{
					throw new \Exception("Missing attribute in dataset.");
				}
				else
				{
					continue; /* Ignore. */
				}
			}
			
			if($settings["type"] == "custom")
			{
				/* This was already processed in the results -> serialized step, just treat it as a string. */
				$attributes[$attribute] = $data[$attribute];
			}
			else
			{
				switch($settings["type"])
				{
					case "string":
						$value = $data[$attribute];
						break;
					case "numeric":
						/* Cast back to a float or int. */
						if(strpos($data[$attribute], ".") !== false)
						{
							$value = (float) $data[$attribute];
						}
						else
						{
							$value = (int) $data[$attribute];
						}
						break;
					case "timestamp":
						/* Cast back to an int. */
						$value = (int) $data[$attribute];
						break;
					case "boolean":
						/* Don't touch it. */
						$value = $data[$attribute];
					default:
						/* This is a resource identifier. We'll just set it as a string value, and
						 * let the Resource object resolve it when requested through __get. */
						$value = $data[$attribute];
						break;
				}
				
				$attributes[$attribute] = $value;
			}
		}
		
		return $attributes;
	}
	
	public function ObtainResourceList($type, $filters)
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
	
	public function ObtainResource($type, $filters)
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
	
	public function BlankResource($type)
	{
		return new Resource($this, $type, $this->config["resources"][$type]);
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
	
	/* RegisterTypeEncoder and RegisterTypeDecoder work similarly,
	 * except their scope is custom types/serializations rather than
	 * specific attributes on specific resource types. You'd use custom
	 * types for context-independent custom serialization, such as
	 * unusually formatted date/time strings. */
	public function RegisterTypeEncoder($type, $attribute, $function)
	{
		if(!isset($this->custom_type_encoder[$type]))
		{
			$this->custom_type_encoder[$type]  = array();
		}
		
		$this->custom_type_encoder[$type][$attribute] = $function;
	}
	
	public function RegisterTypeDecoder($type, $attribute, $function)
	{
		if(!isset($this->custom_type_decoder[$type]))
		{
			$this->custom_type_decoder[$type]  = array();
		}
		
		$this->custom_type_decoder[$type][$attribute] = $function;
	}
	
	public function RegisterAuthenticator($name, $function)
	{
		$this->authenticator[$name] = $function;
	}
		
	/* The following functions are for cryptographical request signing as authentication
	 * method. A unique nonce must always be provided; ideally, this is cryptographically
	 * secure random data. */
	
	protected function RegisterNonce($api_id, $nonce)
	{
		/* The expiry must be specified as an expiry timestamp. */
		$safe_nonce = str_replace(".", "%2E", urlencode($nonce)); /* Sigh... */
		$nonce_dir = sys_get_temp_dir() . "/cphp-rest-nonce/{$api_id}";
		$nonce_path = $nonce_dir . "/" . $nonce;
		@mkdir($nonce_dir, 0700, true);
		$handle = @fopen($nonce_path, "x");
		
		if($handle === false)
		{
			/* Nonce was already registered. Check for expiry. */
			$modified = stat($nonce_path)["mtime"];
			
			if($modified < time() - $this->expiry)
			{
				/* Remove and re-create the lockfile. */
				unlink($nonce_path);
				$handle = fopen($nonce_path, "x");
			}
			else
			{
				throw new NonceException("That nonce has already been used.");
			}
		}
		
		fclose($handle);
		
		/* TODO: Internal housekeeping by cleaning up expired entries
		 * every X time? */
		/* TODO: Attempt to register a nonce; if failure, check expiry
		 * time to see if it can override. */
	}
	
	protected function CreateSTS($verb, $uri, $get_data, $post_data, $nonce, $expiry)
	{
		$sts = ""; /* Start out with an empty STS. */
		$sts .= $nonce . "\n"; /* Append the nonce and a newline. */
		$sts .= $expiry . "\n"; /* Append the expiry timestamp and a newline. */
		$sts .= strtoupper($verb) . "\n"; /* Append the request method (HTTP verb) in uppercase, and append a newline. */
		$uri = ends_with($uri, "/") ? substr($uri, 0, strlen($uri) - 1) : $uri; /* Remove the trailing slash from the URI if it exists. */
		$sts .= $uri . "\n"; /* Append the requested URI, in the form /some/thing, and append a newline. */
		
		/* GET data is a little more complicated... We need to sort the POST data by
		 * array key initially - however, if multiple values exist for a key (as is the case
		 * for GET field arrays), the second sorting criterium is the value. All sorting
		 * should be case-insensitive. After sorting, a query string should be built from
		 * the sorted GET data. Spaces are encoded as +. A newline is appended
		 * afterwards. */
		
		uksort($get_data, function($a, $b) { return strcasecmp($a, $b); });
		foreach($get_data as $key => &$values)
		{
			if(is_array($values))
			{
				usort($values, function($a, $b) { return strcasecmp($a, $b); });
			}
		}
		$sts .= http_build_query($get_data) . "\n";
		
		/* POST data is handled basically the same way. Don't forget the trailing
		 * newline! */
		uksort($post_data, function($a, $b) { return strcasecmp($a, $b); });
		foreach($post_data as $key => &$values)
		{
			if(is_array($values))
			{
				usort($values, function($a, $b) { return strcasecmp($a, $b); });
			}
		}
		$sts .= http_build_query($post_data) . "\n";
		
		return $sts;
	}
	
	protected function CreateSignature($signing_key, $verb, $uri, $get_data, $post_data, $nonce, $expiry)
	{
		$sts = $this->CreateSTS($verb, $uri, $get_data, $post_data, $nonce, $expiry);
		
		/* When done building the STS, we sign it and return the base64-encoded version.
		 * HMAC + SHA512 is to be used. */
		return base64_encode(hash_hmac("sha512", $sts, $signing_key, true));
	}
	
	public function Sign($signing_key, $verb, $uri, $get_data, $post_data, $nonce, $expiry)
	{
		return $this->CreateSignature($signing_key, $verb, $uri, $get_data, $post_data, $nonce, $expiry);
	}
	
	public function VerifySignature($signature, $signing_key, $verb, $uri, $get_data, $post_data, $nonce, $expiry)
	{
		return ($signature === $this->CreateSignature($signing_key, $verb, $uri, $get_data, $post_data, $nonce, $expiry));
	}
}

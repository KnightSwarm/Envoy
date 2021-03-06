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

class Handler extends ResourceBase
{
	function __construct($api, $object, $handler_name, $parameters)
	{
		$this->api = $api;
		$this->object = $object;
		$this->handler_name = $handler_name;
		$this->parameters = $parameters;
	}
}

<?php
$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

$_CPHP_REST = true;
require("cphp-rest/base.php");

use \CPHP\REST;

$API = new \CPHP\REST\API();
$API->LoadConfiguration("../../api.json");

$API->RegisterDecoder("room", "jid", function($api, $value, $filters){
	list($roomname, $fqdn) = explode("@", $value, 2);
	$fqdn = $api->Fqdn($fqdn);
	return array("fqdn" => $fqdn->id, "roomname" => $roomname);
});

$API->RegisterEncoder("room", "jid", function($api, $resource){
	return "{$resource->roomname}@{$resource->fqdn->fqdn}";
});

$API->RegisterDecoder("user", "jid", function($api, $value, $filters){
	list($username, $fqdn) = explode("@", $value, 2);
	return array("fqdn_string" => $fqdn, "username" => $username);
});

$API->RegisterEncoder("user", "jid", function($api, $resource){
	return "{$resource->username}@{$resource->fqdn_string}";
});

$API->RegisterEncoder("user", "full_name", function($api, $resource){
	return "{$resource->first_name} {$resource->last_name}";
});

$API->RegisterEncoder("api_key", "access_level", function($api, $resource){
	try
	{
		/* Find service-wide permissions, if any. */
		$permissions = $resource->ListPermissions(array("fqdn" => 0));
	}
	catch (NotFoundException $e)
	{
		/* No service-wide permissions. */
		$permissions = array();
	}
	
	/* Master (server-only) access. */
	foreach($permissions as $permission)
	{
		if($permission->access_level == 200 && $resource->type == "server")
		{
			return 200;
		}
	}
	
	/* Service-administrative access. */
	foreach($permissions as $permission)
	{
		if($permission->access_level == 150 && $resource->user->access_level >= 150)
		{
			return 150;
		}
	}
	
	/* There are no service-wide permissions for this key. Return 0 and
	 * let the authenticators sort out the FQDN-specific permissions. */
	return 0;
});

//$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local/affiliations";
//$_GET = array("affiliation" => "owner");
//$_SERVER["REQUEST_URI"] = "/rooms/testingroom13@envoy.local";
//$_SERVER["REQUEST_URI"] = "/users";

$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local";

/* This is just for testing purposes... emulating signature generation. */
$signing_key = "test";
$verb = "GET";
$uri = $_SERVER["REQUEST_URI"];
$nonce = random_string(15);
$expiry = time() + $API->expiry;
$_SERVER['HTTP_API_SIGNATURE'] = $API->Sign($signing_key, $verb, $uri, $_GET, $_POST, $nonce, $expiry);
/* End testing block... */

$_SERVER["HTTP_API_ID"] = "test";
$_SERVER["HTTP_API_EXPIRY"] = $expiry;
$_SERVER["HTTP_API_NONCE"] = $nonce;

$API->ProcessRequest();
//pretty_dump($API->Room("testingroom13@envoy.local")->ListAffiliations(array("affiliation" => "owner"))[0]->user->full_name);

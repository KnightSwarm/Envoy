<?php
$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

$_CPHP_REST = true;
require("cphp-rest/base.php");

use \CPHP\REST;

//$API = new \CPHP\REST\APIClient("http://api.envoy.local:8080");
$API = new \CPHP\REST\APIClient("http://api.envoy.local");
$API->LoadConfiguration("../../api.json"); 
$API->Authenticate("test", "test");

try
{
	//pretty_dump($API->Fqdn("envoy.local")->Room("testingroom13")->Notify(array("message" => "Hi!")));
	//pretty_dump($API->Fqdn("envoy.local")->owner->jid);
	/*foreach($API->Fqdn("envoy.local")->Room("testingroom13")->ListAffiliations() as $affiliation)
	{
		echo("<strong>{$affiliation->user->jid}</strong>: ({$affiliation->room->jid}) {$affiliation->affiliation}<br>");
	}*/
	//pretty_dump($API->Fqdn("envoy.local")->fqdn);
	/*$new_user = $API->Fqdn("envoy.local")->User();
	$new_user->username = "blah";
	$new_user->DoCommit();*/
	//$aff = $API->Fqdn("envoy.local")->User("testuser")->Affiliation();
	//$aff->room = $API->Fqdn("envoy.local")->Room("testingroom13");
	//$aff = $API->Affiliation(38);
	//$aff->affiliation = "owner";
	//$aff->DoCommit();
	//$aff->DoDelete();
	//pretty_dump($aff);
	foreach($API->Fqdn("envoy.local")->ListAffiliations() as $affiliation)
	{
		pretty_dump("{$affiliation->room->roomname}: {$affiliation->user->username} ({$affiliation->affiliation})");
	}
}
catch (CPHP\REST\ApiException $e)
{
	/* FIXME: Remove in final. */
	echo("API ERROR: " . $e->GetApiMessage());
	throw $e;
}

die();


$API = new \CPHP\REST\APIServer();
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
		$permissions = $resource->ListPermissions(array("fqdn" => 0), true);
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

$API->RegisterHandler("room", "notify", function($room) {
	$handler = new CPHPFormHandler($_POST, true);
	
	try
	{
		$handler
			->RequireNonEmpty("message")
			->Done();
	}
	catch (FormValidationException $e)
	{
		/* FIXME: Throw HTTP error for invalid input.. 410? */
	}
	
	$context = new ZMQContext();
	$query_socket = new ZMQSocket($context, ZMQ::SOCKET_PUSH);
	$query_socket->connect("tcp://127.0.0.1:18081");

	$payload = array(
		"type" => "room_notification",
		"args" => array(
			"room" => $room->jid,
			"color" => $handler->GetValue("color", "yellow"),
			"message" => $handler->GetValue("message"),
			"notify" => $handler-> GetValue("notify", "0"),
			"message_format" => $handler->GetValue("message_format", "html")
		)
	);
	
	$query_socket->send(json_encode($payload));
	
	return true;
});

//$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local/affiliations";
//$_GET = array("affiliation" => "owner");
//$_SERVER["REQUEST_URI"] = "/rooms/testingroom13@envoy.local";
//$_SERVER["REQUEST_URI"] = "/users";

//$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local";
$_SERVER["REQUEST_URI"] = "/rooms/testingroom13@envoy.local/notify";

$_POST["message"] = "This is a sample message.";
$_POST["color"] = "red";

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

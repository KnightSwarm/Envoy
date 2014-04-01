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

$API->RegisterEncoder("room", "jid", function($api, $attributes){
	$fqdn = $api->ObtainResource("fqdn", array("id" => $attributes["fqdn"]));
	return "{$attributes['roomname']}@{$fqdn->fqdn}";
});

$API->RegisterDecoder("user", "jid", function($api, $value, $filters){
	list($username, $fqdn) = explode("@", $value, 2);
	return array("fqdn_string" => $fqdn, "username" => $username);
});

$API->RegisterEncoder("user", "jid", function($api, $attributes){
	return "{$attributes['username']}@{$attributes['fqdn_string']}";
});

$API->RegisterEncoder("user", "full_name", function($api, $attributes){
	return "{$attributes['first_name']} {$attributes['last_name']}";
});

//$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local/affiliations";
//$_SERVER["REQUEST_URI"] = "/rooms/testingroom13@envoy.local";
//$API->ProcessRequest();
pretty_dump($API->Room("testingroom13@envoy.local")->ListAffiliations(array("affiliation" => "owner"))[0]->user->full_name);

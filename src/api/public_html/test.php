<?php
$_CPHP = true;
$_CPHP_CONFIG = "../../config.json";
require("cphp/base.php");

$_CPHP_REST = true;
require("cphp-rest/base.php");

use \CPHP\REST;

$API = new \CPHP\REST\API();
$API->LoadConfiguration("../../api.json");

$API->RegisterDecoder("user", "jid", function($value, $filters){
	list($username, $fqdn) = explode("@", $value, 2);
	return array("fqdn_string" => $fqdn, "username" => $username);
});

$API->RegisterEncoder("user", "jid", function($attributes){
	return "{$attributes['username']}@{$attributes['fqdn_string']}";
});

$API->RegisterEncoder("user", "full_name", function($attributes){
	return "{$attributes['first_name']} {$attributes['last_name']}";
});

$_SERVER["REQUEST_URI"] = "/users/testuser@envoy.local/affiliations";
$API->ProcessRequest();

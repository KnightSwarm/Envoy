<?php

require("base.php");

$api = new EnvoyLib\Api("http://api.envoy.local/", "test1", "test1");
$fqdn = $api->CreateFqdn("testfqdn.local", "Random FQDN", "testuser", "testpass", "optional description goes here");
var_dump($fqdn->name);

<?php

require("base.php");

$api = new EnvoyLib\Api("http://api.envoy.local/", "test", "test");
$user = $api->CreateUser("secondtest", "envoy.local", "test");
var_dump($user);

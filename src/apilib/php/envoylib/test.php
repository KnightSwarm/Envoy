<?php

require("base.php");

$api = new EnvoyLib\Api("http://api.envoy.local/", "test", "test");
$user = $api->User("secondtest", "envoy2.local");
var_dump($user->VerifyPassword("blah"));
var_dump($user->VerifyPassword("test"));

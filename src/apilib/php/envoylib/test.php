<?php

require("base.php");

$api = new EnvoyLib\Api("http://api.envoy.local/", "test", "test");
$user = $api->User("joepie91", "envoy.local");
var_dump($user->is_activated);

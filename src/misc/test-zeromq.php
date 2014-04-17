<?php

$context = new ZMQContext();
$query_socket = new ZMQSocket($context, ZMQ::SOCKET_REQ);

$query_socket->connect("tcp://127.0.0.1:18081");

$query_socket->send(json_encode(array(
	"type" => "create_room"
)));

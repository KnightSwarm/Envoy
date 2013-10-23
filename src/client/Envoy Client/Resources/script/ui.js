var envoyClient = angular.module('envoyClient', []);
 
envoyClient.controller('UiController', function UiController($scope)
{
	$scope.rooms = [];
	$scope.current_room = "lobby";
	
	$scope.users = [
		{
			"name": "John Doe",
			"status": "available"
		},
		{
			"name": "Jane Doe",
			"status": "busy"
		},
		{
			"name": "Tom Smith",
			"status": "away"
		},
		{
			"name": "James Miller",
			"status": "offline"
		}
	];
	
	$scope.own_jid = "johndoe@fqdn.local";
	
	$scope.messages = [
		{
			"author_name": "John Doe",
			"jid": "johndoe@fqdn.local",
			"body": "Hi, testing"
		},
		{
			"author_name": "John Doe",
			"jid": "johndoe@fqdn.local",
			"body": "Testing more..."
		},
		{
			"author_name": "Jane Doe",
			"jid": "janedoe@fqdn.local",
			"body": "Reply from someone else in the room"
		}
	];
	
	$scope.all_rooms = [
		{
			"name": "Testing room 1",
			"description": "A testing room, number one.",
			"icon": "comments"
		},
		{
			"name": "Testing room 2",
			"description": "A testing room, number two.",
			"icon": "comments"
		},
		{
			"name": "Testing room 3",
			"description": "A testing room, number three.",
			"icon": "lock"
		}
	];
});

var envoyClient = angular.module('envoyClient', []);
 
envoyClient.controller('UiController', function UiController($scope)
{
	$scope.rooms = [
		{
			"name": "Test Room One",
			"icon": "comments",
			"roomname": "testroom1"
		},
		{
			"name": "Test Room Two",
			"icon": "comments",
			"roomname": "testroom2"
		},
		{
			"name": "Private Room Three",
			"icon": "lock",
			"roomname": "testroom3"
		}
	];
});

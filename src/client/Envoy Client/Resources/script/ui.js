var envoyClient = angular.module('envoyClient', []);
 
envoyClient.controller('RoomController', function RoomController($scope){
	$scope.room.members = [];
	$scope.room.participants = [];
	$scope.room.all_users = [];
	
	$scope.$watch(function () { return [$scope.room.participants, $scope.room.members]; }, function (val) {
		$scope.room.all_users = _.sortBy(_.uniq(_.union($scope.room.participants, $scope.room.members), false, function(item){ return item.jid; }), "nickname");
	}, true)
});
 
envoyClient.controller('UiController', function UiController($scope)
{
	$scope.rooms = [];
	$scope.current_room = "lobby";
	
	$scope.joined_rooms = [];
	
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
	
	$scope.all_rooms = [];
	
	$scope.join_room = function(jid)
	{
		if(_.contains($scope.joined_rooms, jid) == false)
		{
			$scope.joined_rooms.push(jid);
			backend.join_room(jid)
		}
		
		$scope.current_room = jid;
	}
	
	$scope.leave_room = function(jid)
	{
		backend.leave_room(jid);
		/* FIXME: Switch to next closest room */
		$scope.current_room = "lobby";
	}
});

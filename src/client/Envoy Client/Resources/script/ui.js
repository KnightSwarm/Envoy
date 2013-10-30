var envoyClient = angular.module('envoyClient', []);
 
envoyClient.controller('RoomController', function RoomController($scope){
	$scope.room.members = [];
	$scope.room.participants = [];
	$scope.room.all_users = [];
	
	$scope.room.messages = [];
	$scope.room.events = [];
	$scope.room.all_messages = [];
	
	$scope.$watch(function () { return [$scope.room.participants, $scope.room.members]; }, function (val) {
		$scope.room.all_users = _.sortBy(_.uniq(_.union($scope.room.participants, $scope.room.members), false, function(item){ return item.jid; }), "nickname");
	}, true)
	
	$scope.$watch(function () { return [$scope.room.messages, $scope.room.events]; }, function (val) {
		$scope.room.all_messages = _.sortBy(_.union($scope.room.messages, $scope.room.events), function(item){ return item.timestamp.getTime(); });
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
	
	$scope.own_jid = "testuser@envoy.local"; /* FIXME: Set to actual own JID upon connecting */
	
	$scope.all_rooms = [];
	
	$scope.join_room = function(jid)
	{
		if(_.contains($scope.joined_rooms, jid) == false)
		{
			$scope.joined_rooms.push(jid); /* FIXME: Is this really necessary? */
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

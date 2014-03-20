var envoyClient = angular.module('envoyClient', ["luegg.directives"]);
 
envoyClient.controller('RoomController', function RoomController($scope){
	$scope.room.members = [];
	$scope.room.participants = [];
	$scope.room.all_users = [];
	
	$scope.room.messages = [];
	$scope.room.events = [];
	$scope.room.all_messages = [];
	
	$scope.$watch(function () { return [$scope.room.participants, $scope.room.members]; }, function (val) {
		$scope.room.all_users = _.filter(
			_.sortBy(
				_.uniq(
					_.union($scope.room.participants, $scope.room.members)
				, false, function(item){ 
					return item.jid; 
				})
			, "nickname")
		, function(item) {
			return item.nickname != "Envoy_Component"; 
		});
	}, true);
	
	$scope.$watch(function () { return [$scope.room.messages, $scope.room.events]; }, function (val) {
		$scope.room.all_messages = _.sortBy(_.union($scope.room.messages, $scope.room.events), function(item){ return item.timestamp; });
	}, true);
});
 
envoyClient.controller('UiController', function UiController($scope)
{
	$scope.data = {
		input_message: "blah",
		current_room: "lobby",
		rooms: [],
		joined_rooms: [],
		users: [],
		own_jid: "testuser@envoy.local", /* FIXME: Set to actual own JID upon connecting */
		all_rooms: []
	};
	
	$scope.join_room = function(jid)
	{
		if(_.contains($scope.data.joined_rooms, jid) == false)
		{
			$scope.data.joined_rooms.push(jid); /* FIXME: Is this really necessary? */
			backend.join_room(jid)
		}
		
		$scope.data.current_room = jid;
	}
	
	$scope.leave_room = function(jid)
	{
		backend.leave_room(jid);
		/* FIXME: Switch to next closest room */
		$scope.current_room = "lobby";
	}
	
	$scope.format_time = function(time)
	{
		if(moment().isSame(moment.unix(time), "day"))
		{
			/* Today */
			return moment.unix(time).format("HH:mm");
		}
		else
		{
			/* Past */
			return moment.unix(time).format("D MMM, HH:mm");
		}
	}
	
	$scope.send_message = function(event)
	{
		backend.send_group_message($scope.data.input_message, $scope.data.current_room);
		$scope.data.input_message = "";
		/* Hack to keep input focused, should write a directive for this at some point... */
		$("#input_field").focus();
	}
	
	$scope.get_room_object = function(jid)
	{
		return _.filter($scope.data.rooms, function(item){
			return (item.jid == jid); }
		)[0];
	}
});

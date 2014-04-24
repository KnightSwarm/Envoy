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

envoyClient.filter("trusted", function($sce) {
	return function(text) {
		return $sce.trustAsHtml(text);
	}
});

envoyClient.service("vcardService", function vcardService($rootScope) {
	this.get_user = function(jid)
	{
		/* This function attempts to retrieve vCard data associated
		 * with the user. If no such data exists yet, a request for it
		 * will be made to the XMPP server, and the results will be
		 * stored. The built-in cacheing in SleekXMPP is not used for
		 * two reasons: implementing this separately makes it easier
		 * to trigger purges later on, and also makes cacheing work
		 * universally, regardless of backend. */
		 
		jid = new _JID(jid).bare; /* Always operate on bare JIDs... */
		 
		if(typeof $rootScope.data.users[jid] !== "undefined" && typeof $rootScope.data.users[jid].vcard !== "undefined")
		{
			return $rootScope.data.users[jid].vcard;
		}
		else
		{
			if(typeof $rootScope.data.users[jid] == "undefined")
			{
				$rootScope.data.users[jid] = {};
			}
			
			var vcard_data = backend.get_vcard(jid);
			$rootScope.data.users[jid].vcard = vcard_data;
			return vcard_data;
		}
	}
	
	this.get_nick = function(nick)
	{
		for(jid in $rootScope.data.users)
		{
			var user = $rootScope.data.users[jid];
			
			if(user.vcard && user.vcard.nickname[0] == nick)
			{
				return jid;
			}
		}
	}
});

envoyClient.controller("UserController", function UserController($scope, vcardService){
	$scope.user.vcard = vcardService.get_user($scope.user.jid);
	$scope.user.messages = [];
	$scope.user.message_count = 0;
	$scope.user.messages_read = 0;
});
 
envoyClient.controller("MessageController", function MessageController($scope, vcardService){
	$scope.message.vcard = vcardService.get_user($scope.message.jid);
});
 
envoyClient.controller('UiController', function UiController($scope, $rootScope, vcardService)
{
	$scope.data = {
		input_message: "",
		current_room: "lobby",
		rooms: [],
		private_conversations: [],
		tabs: [],
		joined_rooms: [],
		own_jid: "",
		all_rooms: [],
		logged_in: false,
		login_busy: false,
		login_failed: false,
		login_error: ""
	};
	
	/* The rootScope is shared across controllers; we use this as a
	 * place to keep vCard data, and perhaps other application-wide
	 * data at a later point in time. */
	$rootScope.data = {
		users: {}
	};
	
	$scope.join_room = function(jid)
	{
		if(_.contains($scope.data.joined_rooms, jid) == false)
		{
			$scope.data.joined_rooms.push(jid); /* FIXME: Is this really necessary? */
			backend.join_room(jid)
			backend.bookmark_room(jid);
		}
		
		$scope.data.current_room = jid;
	}
	
	$scope.leave_room = function(jid)
	{
		backend.leave_room(jid);
		backend.remove_bookmark(jid)
		/* FIXME: Switch to next closest room */
		$scope.current_room = "lobby";
	}
	
	$scope.switch_user = function(user)
	{
		$scope.data.current_room = user.jid;
		user.messages_read = user.message_count;
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
		if(_.contains(_.pluck($scope.data.private_conversations, "jid"), $scope.data.current_room))
		{
			/* Private conversation */
			window.log("Sending private message");
			backend.send_private_message($scope.data.input_message, $scope.data.current_room);
			
			/* We don't get the message 'echoed' back, so we need to push it onto
			 * the message list manually. */
			 
			var vcard = vcardService.get_user($scope.data.own_jid);
			
			/* Awful hack... TODO: use broadcasts? */
			$userScope = angular.element("#main .chat[data-jid='" + $scope.data.current_room + "']").scope();
			
			/* FIXME: Preview resolution? */
			/* FIXME: Generate message ID */
			
			data = {
				"type": "message",
				"jid": $scope.data.own_jid,
				"nickname": vcard.nickname,
				"fullname": vcard.full_name,
				"body": $scope.data.input_message,
				"timestamp": moment().format("X"),
				"preview": ""
			}
			
			$userScope.user.messages.push(data);
		}
		else
		{
			/* We'll assume it's a room. */
			window.log("Sending group message")
			if($scope.data.input_message.match(/^\/aff(iliation)? /))
			{
				/* Command to set affiliation. */
				var parts = /^\/aff(?:iliation)? (\S+) (\S+)/.exec($scope.data.input_message);
				var nickname = parts[1];
				var affiliation = parts[2];
				var target_jid = vcardService.get_nick(nickname);
				
				if(target_jid)
				{
					backend.set_affiliation($scope.data.current_room, target_jid, affiliation);
				}
				else
				{
					/* FIXME: Logging! */
					console.log("No target JID found!", nickname, vcardService, vcardService.get_nick(nickname));
				}
			}
			else
			{
				backend.send_group_message($scope.data.input_message, $scope.data.current_room);
			}
		}
		
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
	
	$scope.login = function()
	{
		if($scope.data.login_busy == false)
		{
			jid = new _JID($scope.data.username);
			$scope.data.login_busy = true;
			start_client(jid.node, jid.fqdn, $scope.data.password);
		}
	}
	
	$scope.start_private_conversation = function(jid, autofocus)
	{
		if(typeof autofocus == "undefined") { var autofocus = true; };
		
		if(new _JID(jid).bare !== $scope.data.own_jid)
		{
			if(_.contains(_.pluck($scope.data.private_conversations, "jid"), jid) === false)
			{
				/* Create the new tab first. */
				
				var vcard = vcardService.get_user(jid);
				
				if(!vcard || typeof vcard.full_name == "undefined")
				{
					/* FIXME: Logging! */
					var full_name = new _JID(jid).node;
				}
				else
				{
					var full_name = vcard.full_name;
				}
				
				$scope.data.private_conversations.push({
					"type": "user",
					"name": full_name,
					"jid": jid,
					"icon": "user"
				});
			}
			
			if(autofocus)
			{
				$scope.data.current_room = jid;
			}
		}
	}
	
	$scope.end_private_conversation = function(jid)
	{
		$scope.data.private_conversations = $scope.data.private_conversations.filter(function(x, i, a) { return x.jid !== jid; });
		$scope.data.current_room = "lobby";
	}
	
	if(settings.getString("username") !== "" && typeof settings.getString("username") !== "undefined")
	{
		$scope.data.username = settings.getString("username");
	}
	
	if(settings.getString("password") !== "" && typeof settings.getString("password") !== "undefined")
	{
		$scope.data.password = settings.getString("password");
	}
	
	if($scope.data.username !== "" && typeof $scope.data.username !== "undefined" && $scope.data.password !== "" && typeof $scope.data.password !== "undefined")
	{
		/* Trigger automatic login... */
		$scope.login();
	}
});


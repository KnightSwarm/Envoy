/* FIXME: This is a very nasty way to force the event loop to be synchronous. It should
 * probably be improved. Synchronous behaviour is required to prevent events from
 * being executed in the wrong order, as some events may rely on the results of
 * previous events. */
event_loop_processing = false;
var ssl_interval = null;
var reconnect_interval = null;

var event_handlers = {
	login_success: {
		scope: ["ui"],
		handler: function($scope, data) {
			$scope.data.logged_in = true;
			$scope.data.login_failed = false;
			$scope.data.login_busy = false;
			$scope.data.ssl_broken = false;
			$scope.data.ssl_testing = false;
			$scope.data.reconnecting = false;
			$scope.data.own_jid = $scope.data.username;
			
			if(ssl_interval !== null)
			{
				clearInterval(ssl_interval);
			}
			
			if(reconnect_interval !== null)
			{
				clearInterval(reconnect_interval);
			}
			
			settings.setString("username", $scope.data.username);
			settings.setString("password", $scope.data.password);
		}
	},
	login_failed: {
		scope: ["ui"],
		handler: function($scope, data) {
			$scope.data.logged_in = false;
			$scope.data.login_failed = true;
			$scope.data.login_error = data["error_type"];
			$scope.data.login_busy = false;
		}
	},
	disconnected: {
		scope: ["ui"],
		handler: function($scope, data) {
			$scope.data.login_failed = true;
			$scope.data.login_busy = false;
			
			$scope.$broadcast("reset_client");
			
			if($scope.data.logged_in == true)
			{
				/* We were previously connected. */
				$scope.data.login_error = "reconnecting";
				$scope.data.reconnecting = true;
				
				reconnect_interval = setInterval(function(){
					$scope.login();
				}, 10000);
			}
			else if($scope.data.reconnecting == false)
			{
				/* The connection never succeeded. Server down? */
				$scope.data.login_error = "unavailable";
				
				if(!has_tide && $scope.data.ssl_testing == false && $scope.data.ssl_broken == false)
				{
					/* If we're running in web client mode, check to see if there might be
					 * a problem with the SSL certificate for WebSockets. Since browsers
					 * seem to silently fail if a certificate error occurs (such as a certificate
					 * being self-signed), the only way we can detect and fix such problems
					 * is by attempting to initiate a plaintext ws:// connection. If this succeeds,
					 * the problem is with the certificate, and we should iframe the wss://
					 * URI with a https:// protocol instead, and instruct the user to click through
					 * whatever warning might be visible. In the meantime, we will continue
					 * attempting to connect over wss:// - if this succeeds, that means the
					 * user successfully marked the certificate as 'trusted', and we can hide
					 * the iframe. */
					$scope.data.ssl_testing = true;
					 
					var url = "ws://" + target_fqdn + ":5280/xmpp-websocket";
					var testconn = window['MozWebSocket'] ? new MozWebSocket(url, "xmpp") : new WebSocket(url, "xmpp");
					
					testconn.onopen = function(){
						/* This worked; there is an SSL problem. */
						$scope.data.ssl_broken = true;
						$scope.$apply();
						$(".ssl-broken .insecure-link").attr("href", "https://" + target_fqdn + ":5281/xmpp-websocket");
						
						ssl_interval = setInterval(function(){
							$scope.login();
						}, 3000);
					}
				}
			}
			
			$scope.data.logged_in = false;
		}
	},
	roomlist_add: {
		scope: ["ui"],
		handler: function($scope, data) {
			$.each(data, function(i, element)
			{
				$scope.data.all_rooms.push(element)
			});
		}
	},
	roomlist_remove: {
		scope: ["ui"],
		handler: function($scope, data) {
			var to_delete = [];
			
			$.each(data, function(i, element)
			{
				to_delete.push(element.jid);
			});
			
			$scope.data.all_rooms = $scope.data.all_rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
		}
	},
	joinlist_add: {
		scope: ["ui"],
		handler: function($scope, data) {
			$.each(data, function(i, element)
			{
				$scope.data.rooms.push(element);
				
				jid = element["jid"];
				
				if(_.contains($scope.data.joined_rooms, jid) == false)
				{
					/* This is here to make the autojoined rooms also appear
					 * in joined_rooms - that way we won't have issues with
					 * the join links on the Lobby page. */
					$scope.data.joined_rooms.push(jid);
				}
			});
		}
	},
	joinlist_remove: {
		scope: ["ui"],
		handler: function($scope, data) {
			var to_delete = [];
	
			$.each(data, function(i, element)
			{
				to_delete.push(element.jid);
			});
			
			$scope.data.rooms = $scope.data.rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
			$scope.data.joined_rooms = $scope.data.joined_rooms.filter(function(x, i, a){ return to_delete.indexOf(x) === -1 });  // FIXME: ?!
		}
	},
	user_status: {
		scope: ["root"],
		handler: function($rootScope, data) {
			var jid = new _JID(data.jid).bare;
			
			if(_.contains($rootScope.users, jid))
			{
				$rootScope.data.users[jid].status = data.status;
			}
			else
			{
				$rootScope.data.users[jid] = {status: data.status};
			}
		}
	},
	user_presence: {
		scope: ["room"],
		get_scope: function(idx, item){
			return item.data.room_jid;
		},
		handler: function($scope, data) {
			if(data.status == "unavailable")
			{
				$scope.room.events.push({
					"type": "event",
					"jid": data.jid,
					"nickname": data.nickname,
					"fullname": data.fullname,
					"event": "leave",
					"timestamp": data.timestamp
				});
				
				$scope.room.participants = _.filter($scope.room.participants, function(item, idx) { return item.nickname != data.nickname; });
			}
			else
			{
				/* FIXME: Abstract this into an add-if-exists function? */
				/* TODO: Support partial updates of presence information */
				new_object = {
					"nickname": data.nickname,
					"fullname": data.fullname,
					"jid": data.jid,
					"status": data.status,
					"role": data.role,
					"affiliation": data.affiliation
				}
				
				var existing = _.filter($scope.room.participants, function(item, idx){ item._index = idx; return item.nickname == data.nickname; });
				
				if(existing.length > 0)
				{
					$scope.room.participants[existing[0]._index] = new_object
				}
				else
				{
					if($scope.room.finished_join)
					{
						/* Only push event if our initial join has finished; we don't want to know about existing users here */
						$scope.room.events.push({
							"type": "event",
							"jid": data.jid,
							"nickname": data.nickname,
							"fullname": data.fullname,
							"event": "join",
							"timestamp": data.timestamp
						});
					}
					
					$scope.room.participants.push(new_object)
				}
				
				if(new _JID(data.jid).bare == $scope.own_jid)
				{
					/* Mark the join as finished; from this point on, joins will be displayed in the client. */
					$scope.room.finished_join = true;
				}
			}
		}
	},
	receive_message: {
		scope: ["room"],
		get_scope: function(index, item){
			return item.data.room_jid;
		},
		handler: function($scope, data) {
			if((data.jid && !data.jid.match(/^component\.[^@]+$/)) || data.body.match(/^\[/))
			{
				data["type"] = "message";
				$scope.room.messages.push(data);
			}
		}
	},
	receive_private_message: {
		scope: ["user"],
		get_scope: function(index, item){
			/* Ensure that a conversation tab for this user exists. */
			var ui_scope = angular.element("[ng-controller=UiController]").scope();
			ui_scope.start_private_conversation(item.data.jid, false);
			/* Force a digest to make sure the element we need, exists... dirty hack. */
			ui_scope.$apply();
			
			return item.data.jid;
		},
		handler: function($scope, data) {
			var ui_scope = angular.element("[ng-controller=UiController]").scope();
			
			/* FIXME: Corner case; delayed (history) stanzas do not include the real JID.
			 * This means we cannot check whether it originated from the component. */
			if((data.jid && !data.jid.match(/^component\.[^@]+$/)) || data.body.match(/^\[/))
			{
				data["type"] = "message";
				$scope.user.messages.push(data);
				$scope.user.message_count += 1;
				
				if(ui_scope.data.current_room == data.jid)
				{
					$scope.user.messages_read = $scope.user.message_count;
				}
				else
				{
					$scope.data.total_unread += 1;
					$scope.update_title();
					
					/* Display notification. */
					Ti.Notification.createNotification({
						title: "Private message from " + data.jid.split("/")[0],
						message: data.body
					}).show();
				}
			}
		}
	},
	preview: {
		scope: ["ui"],
		handler: function($scope, data) {
			$messageScope = angular.element(".message[data-message-id='" + data.message_id + "']").scope();
			if(typeof $messageScope !== "undefined")
			{
				$messageScope.message.preview = data.html;
			}
		}
	},
	vcard: {
		scope: ["root"],
		handler: function($rootScope, data) {
			var jid = data.jid;
			
			/* Create a vCard data object if it doesn't yet exist. */
			if(!$rootScope.data.users[jid].vcard)
			{
				$rootScope.data.users[jid].vcard = {};
			}
			 
			 /* To make sure that any references to the old vCard data
			 * remain functional and are updated with the new vCard
			 * data, we manually copy over all properties to the existing
			 * vCard data object. */
			for(key in data)
			{
				$rootScope.data.users[jid].vcard[key] = data[key];
			}
		}
	}
}

var process_func = function(item){
	event_loop_processing = true;
	
	window.log(item);
	
	if(typeof event_handlers[item.type] !== "undefined")
	{
		var hdl = event_handlers[item.type];
		var scope = undefined;
		
		switch(hdl.scope[0])
		{
			case "root":
				scope = angular.element("[ng-app]").scope();
				break;
			case "ui":
				scope = angular.element("[ng-controller=UiController]").scope();
				break;
			case "room":
			case "user":
				scope = angular.element("#main .chat[data-jid='" + hdl.get_scope(0, item) + "']").scope();
				break;
		}
		
		if(typeof scope !== "undefined")
		{
			hdl.handler(scope, item.data);
			scope.$apply();
		}
		else
		{
			window.log("WARNING: No suitable scope found for event of type '" + item.type + "'!");
		}
	}
	
	/* FIXME: Keep a separate list of 'users to show in userlist' and 'participants',
	 * to compensate for offline room members? */
	
	event_loop_processing = false;
};

if(has_tide)
{
	q.set_callback(process_func);
}

$(function(){
	if(has_tide)
	{
		setInterval(function(){
			if(event_loop_processing == false)
			{
				if(typeof q.check !== "undefined")
				{
					q.check();
				}
				else if(has_tide) /* Only run this check when using the TideSDK backend */
				{
					/* Our backend crashed, restart the client.
					 * TODO: Notify the user, and ask them to submit a log. */
					console.log("CRITICAL: Backend crash detected. reloading client...");
					location.reload();
				}
			}
		}, 150); /* FIXME: This is not very efficient. Surely, there's a better way to do this? */
	}
});

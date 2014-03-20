/* FIXME: This is a very nasty way to force the event loop to be synchronous. It should
 * probably be improved. Synchronous behaviour is required to prevent events from
 * being executed in the wrong order, as some events may rely on the results of
 * previous events. */
event_loop_processing = false;

var event_handlers = {
	login_success: {
		scope: ["ui"],
		handler: function($scope, data) {
			$scope.data.logged_in = true;
			$scope.data.login_failed = false;
			$scope.data.login_busy = false;
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
		scope: ["ui"],
		handler: function($scope, data) {
			if(_.contains($scope.users, data.jid))
			{
				$scope.data.users[data.jid].status = data.status;
			}
			else
			{
				$scope.data.users[data.jid] = {status: data.status};
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
			data["type"] = "message";
			$scope.room.messages.push(data);
		}
	}
}

q.set_callback(function(item){
	event_loop_processing = true;
	
	window.log(item);
	
	if(typeof event_handlers[item.type] !== "undefined")
	{
		var hdl = event_handlers[item.type];
		var scope = undefined;
		
		switch(hdl.scope[0])
		{
			case "ui":
				scope = angular.element("[ng-controller=UiController]").scope();
				break;
			case "room":
				scope = angular.element("#main .chat[data-jid='" + hdl.get_scope(0, item) + "']").scope();
				break;
		}
		
		if(typeof scope !== undefined)
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
});

$(function(){
	setInterval(function(){
		if(event_loop_processing == false)
		{
			q.check();
		}
	}, 150); /* FIXME: This is not very efficient. Surely, there's a better way to do this? */
});

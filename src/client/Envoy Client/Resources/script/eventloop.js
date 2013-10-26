/* FIXME: This is a very nasty way to force the event loop to be synchronous. It should
 * probably be improved. Synchronous behaviour is required to prevent events from
 * being executed in the wrong order, as some events may rely on the results of
 * previous events. */
event_loop_processing = false;

var event_handlers = {
	roomlist_add: {
		scope: ["ui"],
		handler: function($scope, data) {
			$.each(data, function(i, element)
			{
				$scope.all_rooms.push(element)
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
			
			$scope.all_rooms = $scope.all_rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
		}
	},
	joinlist_add: {
		scope: ["ui"],
		handler: function($scope, data) {
			$.each(data, function(i, element)
			{
				$scope.rooms.push(element)
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
			
			$scope.rooms = $scope.rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
			$scope.joined_rooms = $scope.joined_rooms.filter(function(x, i, a){ return to_delete.indexOf(x) === -1 });  // ?!
		}
	},
	user_status: {
		scope: ["ui"],
		handler: function($scope, data) {
			if(_.contains($scope.users, data.jid))
			{
				$scope.users[data.jid].status = data.status;
			}
			else
			{
				$scope.users[data.jid] = {status: data.status};
			}
		}
	},
	user_presence: {
		scope: ["room"],
		get_scope: function(idx, item){
			return item.data.room_jid;
		},
		handler: function($scope, data) {
			if(typeof $scope.room.participants == "undefined")
			{
				$scope.room.participants = [];
			}
			
			/* FIXME: Abstract this into an add-if-exists function? */
			new_object = {
				"nickname": data.nickname,
				"jid": data.jid,
				"status": data.status,
				"role": data.role,
				"affiliation": data.affiliation
			}
			
			var existing = _.filter($scope.room.participants, function(i, idx){ i._index = idx; return i.nickname == data.nickname; });
			
			if(existing.length > 0)
			{
				$scope.room.participants[existing[0]._index] = new_object
			}
			else
			{
				$scope.room.participants.push(new_object)
			}
		}
	}
}

q.set_callback(function(item){
	event_loop_processing = true;
	
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
			console.log("WARNING: No suitable scope found for event of type '" + item.type + "'!");
		}
	}
	
	var ui_scope = angular.element("[ng-controller=UiController]").scope()
	
	console.log(item);
	
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

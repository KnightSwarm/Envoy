/* FIXME: This is a very nasty way to force the event loop to be synchronous. It should
 * probably be improved. Synchronous behaviour is required to prevent events from
 * being executed in the wrong order, as some events may rely on the results of
 * previous events. */
event_loop_processing = false;

q.set_callback(function(item){
	event_loop_processing = true;
	
	var ui_scope = angular.element("[ng-controller=UiController]").scope()
	
	console.log(item);
	
	/* FIXME: Abstract this into something with less boilerplate... */
	/* FIXME: Keep a separate list of 'users to show in userlist' and 'participants',
	 * to compensate for offline room members? */
	
	if(item.type == "roomlist_add")
	{
		$.each(item.data, function(i, element)
		{
			ui_scope.all_rooms.push(element)
		});
	}
	else if(item.type == "roomlist_remove")
	{
		var to_delete = [];
		
		$.each(item.data, function(i, element)
		{
			to_delete.push(element.jid);
		});
		
		ui_scope.all_rooms = ui_scope.all_rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
	}
	else if(item.type == "joinlist_add")
	{
		$.each(item.data, function(i, element)
		{
			ui_scope.rooms.push(element)
		});
	}
	else if(item.type == "joinlist_remove")
	{
		var to_delete = [];
		
		$.each(item.data, function(i, element)
		{
			to_delete.push(element.jid);
		});
		
		ui_scope.rooms = ui_scope.rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
	}
	else if(item.type == "user_status")
	{
		if(_.contains(ui_scope.users, item.data.jid))
		{
			ui_scope.users[item.data.jid].status = item.data.status;
		}
		else
		{
			ui_scope.users[item.data.jid] = {status: item.data.status};
		}
	}
	else if(item.type == "user_presence")
	{
		var room_scope = angular.element("#main .chat[data-jid='" + item.data.room_jid + "']").scope();
		
		if(typeof room_scope.room.participants == "undefined")
		{
			room_scope.room.participants = [];
		}
		
		/* FIXME: Abstract this into an add-if-exists function? */
		new_object = {
			"nickname": item.data.nickname,
			"jid": item.data.jid,
			"status": item.data.status,
			"role": item.data.role,
			"affiliation": item.data.affiliation
		}
		
		var existing = _.filter(room_scope.room.participants, function(i, idx){ i._index = idx; return i.nickname == item.data.nickname; });
		
		if(existing.length > 0)
		{
			room_scope.room.participants[existing[0]._id] = new_object
		}
		else
		{
			room_scope.room.participants.push(new_object)
		}
		
		room_scope.$apply();
	}
	
	ui_scope.$apply();
	
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

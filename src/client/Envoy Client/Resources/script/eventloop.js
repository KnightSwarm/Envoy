q.set_callback(function(item){
	var ui_scope = angular.element("[ng-controller=UiController]").scope()
	
	console.log(item);
	
	if(item.type == "roomlist_add")
	{
		$.each(item.data, function(i, element)
		{
			ui_scope.rooms.push(element)
		});
	}
	else if(item.type == "roomlist_remove")
	{
		var to_delete = [];
		
		$.each(item.data, function(i, element)
		{
			to_delete.push(element.jid);
		});
		
		ui_scope.rooms = ui_scope.rooms.filter(function(x, i, a){ return to_delete.indexOf(x.jid) === -1 });
	}
	
	ui_scope.$apply();
});

$(function(){
	setInterval(q.check, 150); /* FIXME: This is not very efficient. Surely, there's a better way to do this? */
});

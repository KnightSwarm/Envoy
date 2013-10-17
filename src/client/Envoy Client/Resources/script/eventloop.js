q.set_callback(function(item){
	var ui_scope = angular.element("[ng-controller=UiController]").scope()
	
	if(item.type == "roomlist_add")
	{
		ui_scope.rooms.push(item.data)
	}
	
	ui_scope.$apply();
});

$(function(){
	setInterval(q.check, 150); /* FIXME: This is not very efficient. Surely, there's a better way to do this? */
});

var parent = Ti.UI.getCurrentWindow().getParent().getWindow();
var envoyDebug = angular.module('envoyDebug', ["luegg.directives"]);

envoyDebug.controller('DebugConsoleController', function DebugConsoleController($scope){
	$scope.messages = [];
});

function get_scope()
{
	return angular.element("#messages").scope();
}

function application_eval(string)
{
	var app = parent;
	return eval(string);
}

$(function(){
	$("#form_command").submit(function(event){
		var cmd = $(this).find("input#command").val();
		response = application_eval(cmd);
		
		if(typeof response == "undefined" || response == null)
		{
			response = "<null>";
		}
		
		get_scope().$apply(function($scope){ $scope.messages.push({command: cmd, body: response}); });
		return false;
	});
});

var menu = new ApplicationMenu({
	"File": {
		"Quit": function(){ Ti.App.exit(); }
	},
	"Edit": {
		"Preferences": function(){ openPreferences(); }
	},
	"Help": {
		"Quickstart": function(){ openQuickstart(); },
		"Manual": function(){ openManual(); },
		"About": function(){ openAbout(); },
		"Debugger": function(){
			var debugwin = Ti.UI.createWindow({
				url: "app://debug.html",
				id: "debuggerWindow",
				title: "Debugger",
				visible: true
			});
			
			debugwin.open();
		}
	}
});
menu.attachToWindow(Ti.UI.getCurrentWindow());

$(function(){
	dom_load();
});

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
		"About": function(){ openAbout(); }
	}
});
menu.setDefault();

$(function(){
	dom_load();
});

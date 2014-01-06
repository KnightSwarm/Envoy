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

function JID(jid)
{
	this.jid = jid;
	
	var parts = jid.split("/", 1);
	
	if(parts.length >= 1)
	{
		this.bare = parts[0];
		
		var subparts = this.bare.split("@", 1);
		
		if(subparts.length >= 1)
		{
			this.node = subparts[0];
		}
		else
		{
			this.node = "";
		}
		
		if(subparts.length == 2)
		{
			this.fqdn = subparts[1];
		}
		else
		{
			this.fqdn = "";
		}
	}
	else
	{
		this.bare = "";
		this.node = "";
		this.fqdn = "";
	}
	
	if(parts.length == 2)
	{
		this.resource = parts[1];
	}
	else
	{
		this.resource = "";
	}
}

$(function(){
	dom_load();
});

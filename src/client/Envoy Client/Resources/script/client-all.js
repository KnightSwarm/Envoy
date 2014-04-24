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

/* Underscored to prevent conflict with SleekXMPP... */
function _JID(jid)
{
	this.jid = jid;
	
	var parts = jid.split("/", 2);
	
	if(parts.length >= 1)
	{
		this.bare = parts[0];
		
		var subparts = this.bare.split("@", 2);
		
		if(subparts.length >= 1)
		{
			this.node = subparts[0];
		}
		else
		{
			this.node = "";
		}
		window.log(subparts);
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
	
	if(parts.length >= 2)
	{
		this.resource = parts[1];
	}
	else
	{
		this.resource = "";
	}
}

function hook_autofocus()
{
	autofocus_enabled = true;
	
	/* Automatically focus on the input field when the user starts typing... hacky, but works for now. */
	$(document).on("keydown.autofocus", function(event){
		if(autofocus_enabled == true)
		{
			/* We only want to trigger on text-related keys; that is, characters and space/backspace... */
			if((event.which >= 48 && event.which <= 90)
			|| (event.which >= 96 && event.which <= 111)
			|| (event.which >= 186 && event.which <= 222)
			|| event.which == 32
			|| event.which == 8)
			{
				/* ... and only if the input area is currently visible, and no modifier key (ctrl, alt, command) is pressed. */
				if($(".input").hasClass("hidden") == false && !event.ctrlKey && !event.metaKey && !event.altKey)
				{
					$("#input_field").focus();
					
					/* Cross-browser method of placing the caret at the end of the textarea */
					var old_value = $("#input_field").val();
					$("#input_field").val("").val(old_value);
				}
			}
		}
	});
}

function unhook_autofocus()
{
	autofocus_enabled = false;
	
	$(document).off("keydown.autofocus");
}

$(function(){
	$("#input_field").shiftenter({
		metaKey: "ctrl",
		hint: ""
	});
	
	$(document).on("submit", "form", function(){
		/* Hack because AngularJS does not seem to prevent submissions in ng-submit forms under TideSDK... */
		return false;
	});
	
	$("input, select, textarea, button").on("focus.autofocus", function(){ autofocus_enabled = false; });
	$("input, select, textarea, button").on("blur.autofocus", function(){ autofocus_enabled = true; });
	
	/* This is to prevent the autofocus event from firing for every single keystroke, when there is already focus anyway. */
	$("#input_field").on("focus.autofocus_hook", function(){ unhook_autofocus(); });
	$("#input_field").on("blur.autofocus_hook", function(){ hook_autofocus(); });
	
	hook_autofocus();
	
	dom_load();
});

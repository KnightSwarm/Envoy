var has_tide;
var has_python;
var has_localstorage;

try
{
	has_localstorage = ("localStorage" in window && window["localStorage"] !== null);
}
catch (e)
{
	has_localstorage = false;
}

var TideUserSettings = {
	initialize: function() {
		this.settings_file = Ti.Filesystem.getFile(Ti.API.application.dataPath, "user.properties");

		if(this.settings_file.exists())
		{
			this.settings = Ti.App.loadProperties(this.settings_file.nativePath());
			console.log("Loaded settings from file at", this.settings_file.nativePath());
		}
		else
		{
			this.createDefault();
		}
	},
	getBoolean: function(key) {
		try
		{
			return (this.settings.getString(key) == "true");
		}
		catch (e)
		{
			return undefined;
		}
	},
	getString: function(key) {
		try
		{
			return this.settings.getString(key);
		}
		catch (e)
		{
			return undefined;
		}
	},
	getInt: function(key) {
		try
		{
			return this.settings.getInt(key);
		}
		catch (e)
		{
			return undefined;
		}
	},
	getDouble: function(key) {
		try
		{
			return this.settings.getDouble(key);
		}
		catch (e)
		{
			return undefined;
		}
	},
	setBoolean: function(key, value) {
		if(value === false)
		{
			this.settings.setString(key, "false");
		}
		else
		{
			this.settings.setString(key, "true");
		}
	},
	setString: function(key, value) {
		this.settings.setString(key, value);
		this.saveChanges();
	},
	setInt: function(key, value) {
		this.settings.setInt(key, value);
		this.saveChanges();
	},
	setDouble: function(key, value) {
		this.settings.setDouble(key, value);
		this.saveChanges();
	},
	createDefault: function() {
		this.settings = Ti.App.createProperties({
			debug: "false",
			username: "",
			password: ""
		});
		
		console.log("Created new settings file at", this.settings_file.nativePath());
	},
	saveChanges: function() {
		console.log("Saving configuration changes...");
		this.settings.saveTo(this.settings_file.nativePath());
	}
};

var LocalStorageUserSettings = {
	initialize: function() {
		if(typeof localStorage["envoy.settings_initialized"] === "undefined")
		{
			this.createDefault();
		}
	},
	getBoolean: function(key) {
		return (localStorage["envoy." + key] == "true");
	},
	getString: function(key) {
		return localStorage["envoy." + key];
	},
	getInt: function(key) {
		return parseInt(localStorage["envoy." + key]);
	},
	getDouble: function(key) {
		return parseFloat(localStorage["envoy." + key]);
	},
	setBoolean: function(key, value) {
		if(value === false)
		{
			localStorage["envoy." + key] = "false";
		}
		else
		{
			localStorage["envoy." + key] = "true";
		}
	},
	setString: function(key, value) {
		localStorage["envoy." + key] = value;
	},
	setInt: function(key, value) {
		localStorage["envoy." + key] = value.toString();
	},
	setDouble: function(key, value) {
		localStorage["envoy." + key] = value.toString();
	},
	createDefault: function() {
		localStorage["envoy.settings_initialize"] = "true";
		localStorage["envoy.debug"] = "false";
		localStorage["envoy.username"] = "";
		localStorage["envoy.password"] = "";
	}
};

var MockUserSettings = {
	initialize: function() {
		return undefined;
	},
	getBoolean: function(key) {
		return undefined;
	},
	getString: function(key) {
		return undefined;
	},
	getInt: function(key) {
		return undefined;
	},
	getDouble: function(key) {
		return undefined;
	},
	setBoolean: function(key, value) {
		return undefined;
	},
	setString: function(key, value) {
		return undefined;
	},
	setInt: function(key, value) {
		return undefined;
	},
	setDouble: function(key, value) {
		return undefined;
	},
	createDefault: function() {
		return undefined;
	}
};

/* First we'll check whether the TideSDK API is available. */
if(typeof Ti !== "undefined")
{
	has_tide = true;
}
else
{
	/* The TideSDK API is not available. This means that we're probably running in web client mode. */
	has_tide = false;
	
	$(function(){
		/* If the browser used has support for notifications... */
		if(typeof window.webkitNotifications !== "undefined")
		{
			/* Request to show notifications as soon as we can. */
			$("body").on("mousedown.notification_request", function(){
				/* Only ask if we don't already know. */
				if(window.webkitNotifications.checkPermission() == 1)
				{
					window.webkitNotifications.requestPermission();
				}
				
				/* Remove the event, we don't need it anymore. */
				$("body").off("mousedown.notification_request");
			});
		}
	});
	
	
	/* To make stuff not break, we'll implement a shim for the TideSDK API. For now, it doesn't 
	 * actually do anything; later, this shim will implement functionality similar to TideSDK. */
	var Ti = {
		UI: {
			createMenu: function() { return {
				appendItem: function(){},
			}; },
			createMenuItem: function(){ return {
				setSubmenu: function(){},
			}; },
			setMenu: function(){},
			getCurrentWindow: function(){ return {
				setMenu: function(){},
			}; }
		},
		/* The Notification shim *does* actually do something - but only on Webkit browsers. */
		Notification: {
			createNotification: function(options) {
				/* Only attempt to show notifications if we have permission to do so. */
				if(window.webkitNotifications.checkPermission() == 0)
				{
					if(typeof options.icon == "undefined") { options.icon = ""; }
					var notification = window.webkitNotifications.createNotification(options.icon, options.title, options.message);
					return notification;
				}
			}
		}
	}
}

/* Now we'll check if we have Python support. If not, we'll have to fall back to an alternative
 * XMPP implementation. */
if(typeof has_python == "undefined")
{
	/* We don't have Python support. */
	has_python = false;
	
	/* First of all we'll shim the queue; this is normally used to pass data from the SleekXMPP thread
	 * back to the JS part of the code in the main thread - however, as we don't have Python we'll
	 * be using an API instead. This means that we don't *have* a separate thread, so don't really
	 * need a queue either. For the sake of consistent implementation, however, the browser
	 * backend will use a (fake) queue in the same way the TideSDK backend would. */
	function queue_shim() { this.constructor.apply(this, arguments); }
	queue_shim.prototype = {
		constructor: function(arg1) {
			this.queue = [];
			this.check = this.do_check.bind(this);
		},
		set_callback: function(callback) {
			this.callback = callback;
		},
		put: function(data) {
			this.queue.push(data);
		},
		do_check: function(data) {
			while(this.queue.length > 0)
			{
				item = this.queue.shift();
				this.callback(item);
			}
		}
	}
	
	var q = new queue_shim();
}

/* TideSDK, and possibly some other browsers as well, do not appear to support ECMAScript 5 yet. 
 * Therefore, we need a .bind shim to make scroll-glue work.
 * Source: https://gist.github.com/jussi-kalliokoski/978329 */
Function.prototype.bind = Function.prototype.bind || function(to){
		// Make an array of our arguments, starting from second argument
	var	partial	= Array.prototype.splice.call(arguments, 1),
		// We'll need the original function.
		fn	= this;
	var bound = function (){
		// Join the already applied arguments to the now called ones (after converting to an array again).
		var args = partial.concat(Array.prototype.splice.call(arguments, 0));
		// If not being called as a constructor
		if (!(this instanceof bound)){
			// return the result of the function called bound to target and partially applied.
			return fn.apply(to, args);
		}
		// If being called as a constructor, apply the function bound to self.
		fn.apply(this, args);
	}
	// Attach the prototype of the function to our newly created function.
	bound.prototype = fn.prototype;
	return bound;
};

/* We need this to make stuff not break with a "$digest already in progress" error. 
 * Source: http://stackoverflow.com/a/17114810/1332715 */
function safeApply(scope, fn) {
	(scope.$$phase || scope.$root.$$phase) ? fn() : scope.$apply(fn);
}

/* Finally, take care of the settings file... */
if(has_tide)
{
	var settings = TideUserSettings;
	settings.initialize();
	
	if(settings.getBoolean("debug") == true)
	{
		console.log("WARNING: Debug mode enabled.");
		setInterval(function(){
			/* Only works on *nix systems for now! */
			var reload_trigger = Ti.Filesystem.getFile("/tmp/envoy-client-reload");
			
			if(reload_trigger.exists())
			{
				console.log("Reload trigger received, reloading the application...");
				reload_trigger.deleteFile();
				document.location.reload();
			}
		}, 500);
	}
}
else if(has_localstorage)
{
	var settings = LocalStorageUserSettings;
	settings.initialize();
}
else
{
	console.log("WARNING: Not running in TideSDK, and LocalStorage not available! Cannot store or retrieve user settings...");
	/* Setting a mock object, to make the function calls still execute; this
	 * prevents the entire application from breaking. We simply won't be
	 * able to store any user preferences. */
	var settings = MockUserSettings;
}

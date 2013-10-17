var has_tide;
var has_python;

/* First we'll check whether the TideSDK API is available. */
if(typeof Ti !== "undefined")
{
	has_tide = true;
}
else
{
	/* The TideSDK API is not available. This means that we're probably running in web client mode. */
	has_tide = false;
	
	/* To make stuff not break, we'll implement a shim. For now, it doesn't actually do anything; later,
	 * this shim will implement functionality similar to TideSDK. */
	var Ti = {
		UI: {
			createMenu: function() { return {
				appendItem: function(){},
			}; },
			createMenuItem: function(){ return {
				setSubmenu: function(){},
				
			}; },
			setMenu: function(){}
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


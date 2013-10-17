var has_tide;

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

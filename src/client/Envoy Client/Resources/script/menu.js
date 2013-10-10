/* Thin abstraction layer over standard TideSDK menu API, to make syntax nicer. */

function ApplicationMenu(items)
{
	this.original_items = items;
	this.ti_menu = Ti.UI.createMenu();
	this.items = [];
	this.addItems(items);
}

ApplicationMenu.prototype.addItems = function(items)
{
	for(key in items)
	{
		var value = items[key];
		var item = new ApplicationMenuItem(key, value);
		this.items.push(item);
		item.appendToMenu(this.ti_menu);
	}
}

ApplicationMenu.prototype.attachToWindow = function(window)
{
	window.setMenu(this.ti_menu);
}

ApplicationMenu.prototype.setDefault = function()
{
	Ti.UI.setMenu(this.ti_menu);
}

function ApplicationMenuItem(name, subitems)
{
	if(typeof subitems == "function")
	{
		this.has_children = false;
		this.func = subitems;
		this.ti_item = Ti.UI.createMenuItem(key, subitems);
	}
	else
	{
		this.has_children = true;
		this.subitems = subitems;
		this.ti_item = Ti.UI.createMenuItem(key);
		this.menu = new ApplicationMenu(subitems);
		this.ti_item.setSubmenu(this.menu.ti_menu);
	}
}

ApplicationMenuItem.prototype.appendToMenu = function(menu)
{
	menu.appendItem(this.ti_item)
}

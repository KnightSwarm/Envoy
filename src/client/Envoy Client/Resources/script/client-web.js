if(has_python === false)
{
	var dom_load = function()
	{
		console.log("Initialized as web client.");
	}
}

function WebBackend(username, fqdn, password, queue)
{
	/* Constructor */
	var self = this; /* For persistence throughout callbacks. */
	
	self.username = username;
	self.fqdn = fqdn;
	self.password = password;
	self.q = queue;
	
	self.known_rooms = {};
	
	self.client = XMPP.createClient({
		jid: username + "@" + fqdn,
		password: password,
		transport: "websocket",
		wsURL: "wss://" + fqdn + ":5281/xmpp-websocket"
	})
	
	self.client.on("session:started", function(){
		self.client.getRoster();
		self.client.sendPresence();
		
		self.q.put({
			type: "login_success",
			data: {}
		});
		
		console.log("Initialized!");
		
		/* Update the list of available rooms. */
		self._update_roomlist();
		setInterval(self._update_roomlist.bind(self), 300 * 1000);
		
		/* Auto-join all bookmarked rooms.
		 * FIXME: Old-style bookmark storage is currently used by the TideSDK client,
		 * but it seems stanza.io only supports new-style. This should be changed. */
		self.client.getBookmarks(function(blank, response){
			console.log("BOOKMARKS", response);
		})
	});
	
	self.client.on("auth:failed", function(){
		self.q.put({
			type: "login_failed",
			data: {
				error_type: "auth"
			}
		});
	})
	
	self.client.on("*", function(event_name, event_data){
		console.log("EVENT", event_name, event_data);
	});
	
	self.client.connect();
}

WebBackend.prototype._update_roomlist = function()
{
	var self = this;
	
	/* FIXME: Add a method for this to the stanza.io MUC plugin and submit a pullreq. */
	self.client.getDiscoItems("conference.envoy.local", "", function(blank, response){
		var rooms = response.discoItems.items;
		var new_rooms = [];
		
		for(i in rooms)
		{
			var room = rooms[i];
			
			new_rooms.push(room.jid.toString());
			
			if(typeof self.known_rooms[room.jid.toString()] == "undefined")
			{
				/* New room. */
				self.q.put({"type": "roomlist_add", "data": [{
					"type": "room",
					"name": room.name,
					"jid": room.jid.toString(),
					"icon": "comments"
				}]});
				
				self.known_rooms[room.jid.toString()] = room;
			}
		}
		
		for(jid in self.known_rooms)
		{
			var room = rooms[jid];
			
			if(_.contains(new_rooms, jid) == false)
			{
				/* Removed room. */
				self.q.put({"type": "roomlist_remove", "data": [{
					"jid": room.jid.toString()
				}]})
				
				delete self.known_rooms[room.jid.toString()];
			}
		}
	});
}

WebBackend.prototype.join_room = function(room_jid)
{
	
}

WebBackend.prototype.leave_room = function(room_jid)
{
	
}

WebBackend.prototype.bookmark_room = function(room_jid)
{
	
}

WebBackend.prototype.remove_bookmark = function(jid)
{
	
}

WebBackend.prototype.get_vcard = function(jid)
{
	
}

WebBackend.prototype.send_group_message = function(message, room_jid)
{
	
}

WebBackend.prototype.send_private_message = function(message, recipient_jid)
{
	
}

WebBackend.prototype.set_affiliation = function(room, jid, affiliation)
{
	
}

WebBackend.prototype.change_status = function(status)
{
	
}

WebBackend.prototype.change_topic = function(room_jid, topic)
{
	
}

WebBackend.prototype.update_room_list = function()
{
	
}

function FauxQueue(callback)
{
	this.callback = callback;
}

FauxQueue.prototype.put = function(item) {
	this.callback(item);
}

function start_client(username, fqdn, password)
{
	var q = new FauxQueue(process_func);
	window.backend = new WebBackend(username, fqdn, password, q);
}

if(has_python === false)
{
	var dom_load = function()
	{
		console.log("Initialized as web client.");
	}
}

var target_fqdn;

function WebBackend(username, fqdn, password, queue)
{
	/* Constructor */
	var self = this; /* For persistence throughout callbacks. */
	
	self.username = username;
	self.fqdn = fqdn;
	self.jid = username + "@" + fqdn;
	target_fqdn = fqdn; /* For reconnection code... */
	self.password = password;
	self.q = queue;
	
	self.known_rooms = {};
	self.joined_rooms = [];
	self.buffered_joins = {};
	self.known_users = {};
	self.jid_map = {};
	
	self.client = XMPP.createClient({
		jid: self.jid,
		password: password,
		transport: "old-websocket", /* Change to 'websocket' for new (Prosody >= 0.10.x) WebSocket protocol */
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
			for(i in response.privateStorage.bookmarks.conferences)
			{
				var bookmark = response.privateStorage.bookmarks.conferences[i];
				
				if(bookmark.autoJoin)
				{
					self.join_room(bookmark.jid);
				}
			}
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
	
	self.client.on("muc:join", function(presence){
		/* Join successfully finished */
		var room = presence.from.bare;
		
		self.joined_rooms.push(room);
		
		self.q.put({"type": "joinlist_add", "data": [{
			"type": "room",
			"name": self.known_rooms[room].name,
			"jid": room,
			"icon": "comments"
		}]})
		
		/* Process buffered joins. */
		if(typeof self.buffered_joins[room] !== "undefined")
		{
			_.each(self.buffered_joins[room], function(pres){
				self._process_join(pres);
			})
			
			/* Clear buffer */
			self.buffered_joins[room] = [];
		}
		
		/* Finally, process our own join. */
		self._process_join(presence);
	});
	
	self.client.on("muc:available", function(presence){
		/* Somebody else joined the room. Also fires for self. */
		var room = presence.from.bare;
		var nickname = presence.from.resource;
		var user = presence.muc.jid;
		
		if(user.bare === self.jid)
		{
			return;
		}
		
		if(_.contains(self.joined_rooms, room))
		{
			/* Already joined; this is either a status change or a join/part. */
			if(typeof self.known_users[room] == "undefined")
			{
				self.known_users[room] = [];
			}
			
			if(_.contains(self.known_users[room], nick))
			{
				/* Status change or part. */
				if(presence.type == "unavailable")
				{
					/* Part. */
					self._process_part(presence);
				}
				else
				{
					/* Status change. */
					self._process_status_change(presence);
				}
			}
			else
			{
				/* Join. */
				self._process_join(presence);
			}
		}
		else
		{
			if(typeof self.buffered_joins[room] == "undefined")
			{
				self.buffered_joins[room] = [];
			}
			
			self.buffered_joins[room].push(presence);
		}
	});
	
	self.client.on("muc:leave", function(presence){
		/* Leave successfully finished. */
		var room = presence.from.bare;
		
		self.joined_rooms = _.without(self.joined_rooms, room);
		
		self.q.put({"type": "joinlist_remove", "data":[{
			"jid": room
		}]});
	});
	
	self.client.on("muc:unavailable", function(presence){
		/* Somebody else left the room. Also fires for self. */
		var room = presence.from.bare;
		var nickname = presence.from.resource;
		var user = presence.muc.jid;
		
		if(user.bare === self.jid)
		{
			return;
		}
		
		self._process_part(presence);
	});
	
	self.client.on("chat", function(stanza){
		self.q.put({"type": "receive_private_message", "data": {
			"id": stanza.id,
			"jid": stanza.from.toString(),
			"body": stanza.body,
			"timestamp": Date.now() / 1000,
			"preview": ""
		}})
	});
	
	self.client.on("groupchat", function(stanza){
		var room_jid = stanza.from.bare;
		var nick = stanza.from.resource;
		
		if(typeof stanza.delay == "undefined" || typeof stanza.delay.stamp == "undefined")
		{
			/* Real-time message. */
			var stamp = Date.now() / 1000;
		}
		else
		{
			/* Archived/delayed message. */
			var stamp = stanza.delay.stamp.getTime() / 1000;
		}
		
		var real_jid = self._get_real_jid(room_jid, nick);
		
		self.q.put({"type": "receive_message", "data": {
			"id": stanza.id,
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nick,
			"fullname": nick, /* FIXME: vCard data */
			"body": stanza.body,
			"timestamp": stamp,
			"preview": ""
		}})
	});
	
	self.client.on("disconnected", function(stanza){
		self.q.put({type: "disconnected", data: {}});
	})
	
	self.client.on("*", function(event_name, event_data){
		console.log("EVENT", event_name, event_data);
	});
	
	self.client.connect();
}

WebBackend.prototype._register_real_jid = function(presence)
{
	var room_jid = presence.from.bare;
	var nick = presence.from.resource;
	var real_jid = presence.muc.jid.toString();
	var self = this;
	
	if(typeof self.jid_map[room_jid] == "undefined")
	{
		self.jid_map[room_jid] = {};
	}
	
	self.jid_map[room_jid][nick] = real_jid;
}

WebBackend.prototype._get_real_jid = function(room_jid, nick)
{
	var self = this;
	
	if(self.jid_map[room_jid] && self.jid_map[room_jid][nick])
	{
		return self.jid_map[room_jid][nick];
	}
	else
	{
		return undefined;
	}
}

WebBackend.prototype._process_join = function(presence)
{
	var room_jid = presence.from.bare;
	var nick = presence.from.resource;
	var real_jid = presence.muc.jid.toString();
	var self = this;
	
	self._register_real_jid(presence);
	
	if(presence.type !== "unavailable") /* FIXME: Is this necessary? */
	{
		self.q.put({"type": "user_status", "data": {
			"jid": real_jid,
			"status": presence.type,
			"timestamp": Date.now()
		}});
		
		self.q.put({"type": "user_presence", "data": {
			"room_jid": room_jid,
			"jid": real_jid,
			"nickname": nick,
			"fullname": nick, /* FIXME: vCard data */
			"status": presence.type,
			"role": presence.muc.role,
			"affiliation": presence.muc.affiliation,
			"timestamp": Date.now() / 1000
		}})
	}
}

WebBackend.prototype._process_part = function(presence)
{
	/* FIXME */
}

WebBackend.prototype._process_status_change = function(presence)
{
	/* FIXME */
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
	var self = this;
	self.client.joinRoom(room_jid, self.username);
}

WebBackend.prototype.leave_room = function(room_jid)
{
	var self = this;
	self.client.leaveRoom(room_jid, self.username);
}

WebBackend.prototype.bookmark_room = function(room_jid)
{
	var self = this;
	
	self.client.addBookmark({
		autoJoin: true,
		name: room_jid,
		jid: room_jid,
		nick: self.username
	});
}

WebBackend.prototype.remove_bookmark = function(jid)
{
	var self = this;
	
	self.client.removeBookmark(jid);
}

WebBackend.prototype.get_vcard = function(jid)
{
	/* We cannot do this synchronously. Return dummy data, and
	 * fire a "vcard" event when the real data comes in. */
	var self = this;
	
	self.client.getVCard(jid, function(blank, stanza){
		if(typeof stanza == "undefined")
		{
			/* Something went wrong. FIXME: Logging. */
			return;
		}
		
		self.q.put({"type": "vcard", "data": {
			"jid": jid,
			"full_name": stanza.vCardTemp.fullName,
			"job_title": stanza.vCardTemp.title,
			"nickname": stanza.vCardTemp.nicknames,
			"mobile_number": stanza.vCardTemp.phoneNumbers[0].number,
			"email_address": stanza.vCardTemp.emails[0].email
		}});
	});
	
	return {
		"jid": jid,
		"full_name": jid.split("@")[0],
		"job_title": "",
		"nickname": jid.split("@")[0],
		"mobile_number": "",
		"email_address": ""
	} 
}

WebBackend.prototype.send_group_message = function(message, room_jid)
{
	var self = this;
	
	self.client.sendMessage({
		to: room_jid,
		body: message,
		type: "groupchat"
	});
}

WebBackend.prototype.send_private_message = function(message, recipient_jid)
{
	var self = this;
	
	self.client.sendMessage({
		to: recipient_jid,
		body: message,
		type: "chat"
	});
}

WebBackend.prototype.set_affiliation = function(room, jid, affiliation)
{
	var self = this;
	
	console.log(affiliation);
	self.client.setRoomAffiliation(room, jid, affiliation);
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

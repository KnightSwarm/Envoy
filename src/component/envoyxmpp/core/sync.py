from .util import LocalSingleton, LocalSingletonBase, prosody_quote

from sleekxmpp.exceptions import IqError
import os, stat

@LocalSingleton
class PresenceSyncer(LocalSingletonBase):
	def sync(self):
		component = Component.Instance(self.identifier)
		user_provider = UserProvider.Instance(self.identifier)
		presence_provider = PresenceProvider.Instance(self.identifier)
		
		# We will do a two pass here. On the first pass, all missing presences are added. On the second pass, all
		# outdated presences are removed. This way, there won't be any chance of race conditions, as there would
		# be when clearing the table first and then re-filling it.
		
		current_presences = {}
		
		room_list = component['xep_0045'].get_rooms(ifrom=component.boundjid, jid=component.conference_host)['disco_items']['items']
		
		for room in room_list:
			room_jid, room_node, room_name = room
			
			presences = (component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, role="visitor")['muc_admin']['items'] +
			             component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, role="participant")['muc_admin']['items'] +
			             component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, role="moderator")['muc_admin']['items'])
			
			for presence in presences:
				user_jid = presence["jid"]
				resource = presence["jid"].resource
				nickname = presence["nick"]
				role = presence["role"]
				
				if user_jid != component.boundjid: # No need to keep state for the component
					try:
						user_presence = presence_provider.get(room_jid, nickname)
						if user_presence.role != role:
							# EVENT: Sync role change
							user_presence.change_role(role)
					except NotFoundException, e:
						# EVENT: Sync join
						user_object = user_provider.get(user_jid)
						user_object.register_join(room_jid, resource, nickname, role)
					
			current_presences[room_jid] = [user_provider.normalize_jid(presence["jid"], keep_resource=True) for presence in presences]
			
		try:
			known_presences = presence_provider.find_by_fqdn(component.get_fqdn())
		except NotFoundException, e:
			# We don't have any known presences for this FQDN, we're done here...
			return
			
		for presence in known_presences:
			if "%s/%s" % (presence.user.jid, presence.resource) not in current_presences[presence.room.jid]:
				# EVENT: Sync leave
				presence.user.register_leave(presence.room.jid, presence.resource)

@LocalSingleton
class AffiliationSyncer(LocalSingletonBase):
	def sync(self):
		affiliation_provider = AffiliationProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		room_list = component['xep_0045'].get_rooms(ifrom=component.boundjid, jid=component.conference_host)['disco_items']['items']
		
		for room in room_list:
			room_jid, room_node, room_name = room
			
			presences = (component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, affiliation="owner")['muc_admin']['items'] +
			                component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, affiliation="admin")['muc_admin']['items'] +
			                component['xep_0045'].get_users(room_jid, ifrom=component.boundjid, affiliation="member")['muc_admin']['items'])
			                
			for presence in presences:
				user_jid = presence["jid"]
				affiliation = presence["affiliation"]
				
				if user_jid != component.boundjid: # We don't need to keep state for the component
					try:
						user_affiliation = affiliation_provider.find_by_room_user(room_jid, user_jid)
					except NotFoundException, e:
						# Not a known user, log and skip
						logger.warning("Unknown user %s found during affiliation sync!")
						continue
					
					if user_affiliation.affiliation != affiliation:
						# EVENT: Sync affiliation change
						user_affiliation.change(affiliation)

@LocalSingleton
class RoomSyncer(LocalSingletonBase):
	def sync(self):
		room_provider = RoomProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		try:
			all_rooms = room_provider.find_by_fqdn(component.get_fqdn())
		except NotFoundException, e:
			# No rooms for this FQDN at all...
			logger.warning("No rooms found for FQDN %s during sync!" % component.get_fqdn().fqdn)
			
		for room in all_rooms:
			# Always join all rooms.
			component['xep_0045'].join(room.jid, "Envoy_Component")
			
			try:
				info = component['xep_0030'].get_info(jid=room.jid, ifrom=component.boundjid)
				registered = True
			except IqError, e:
				registered = False
				logger.warning("Tried to retrieve room details for %s after joining, but was denied this information!" % room.jid)
			
			needs_reconfiguration = False
			
			# Check if the title is set correctly
			
			titles = []
			
			for identity in info['disco_info']['identities']:
				category, type_, lang, name = identity
				
				if category == "conference" and type_ == "text":
					titles.append(name)
					
			if room.name not in titles: # TODO: Why multiple titles?
				logger.debug("Mismatch for 'title' setting for room %s: %s not in %s" % (room.jid, room.name, repr(titles)))
				needs_reconfiguration = True
			
			# Check if features are set correctly
			
			for feature in info['disco_info']['features']:
				if feature == "muc_membersonly" and room.private != True:
					logger.debug("Mismatch for 'private' setting for room %s: %s vs. %s" % (room.jid, True, room.private))
					needs_reconfiguration = True
				elif feature == "muc_open" and room.private != False:
					logger.debug("Mismatch for 'private' setting for room %s: %s vs. %s" % (room.jid, False, room.private))
					needs_reconfiguration = True
				elif feature == "muc_moderated" and room.archived != True:
					logger.debug("Mismatch for 'moderated' setting for room %s: %s vs. %s" % (room.jid, True, room.moderated))
					needs_reconfiguration = True
				elif feature == "muc_unmoderated" and room.archived != False:
					logger.debug("Mismatch for 'moderated' setting for room %s: %s vs. %s" % (room.jid, False, room.moderated))
					needs_reconfiguration = True
			
			if needs_reconfiguration:
				logger.debug("Room configuration for %s incorrect; attempting reconfiguration" % room.jid)
				self.configure(room)
		
	def configure(self, room):
		# EVENT: Room (re-)configuration
		room_provider = RoomProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		
		room = room_provider.normalize_room(room)
		
		iq = component['xep_0045'].get_room_config(room.jid, ifrom=component.boundjid)
		logger.debug("Received room configuration form for %s" % room.jid)
		form = iq['muc_owner']['form']
		
		configuration = {
			"muc#roomconfig_roomname": room.name,
			"muc#roomconfig_roomdesc": room.description,
			"muc#roomconfig_persistentroom": True,
			"muc#roomconfig_publicroom": bool(not room.private), # Whether room is public/private
			"muc#roomconfig_changesubject": False, # Whether to allow occupants to change subject
			"muc#roomconfig_whois": "anyone", # Turn off semi-anonymous
			"muc#roomconfig_moderatedroom": bool(room.archived), # Whether moderated/archived
			"muc#roomconfig_membersonly": bool(room.private), # Whether members-only
			"muc#roomconfig_historylength": "20",
			"FORM_TYPE": "http://jabber.org/protocol/muc#roomconfig"
		}
		
		form['fields'] = [(item_var, {'value': item_value}) for item_var, item_value in configuration.iteritems()]
		form['type'] = "submit"
		
		new_iq = component.make_iq_set(ifrom=component.boundjid, ito=room.jid, iq=iq)
		new_iq.send()
		
		logger.debug("Room configuration form for %s filled in and submitted" % room.jid)

@LocalSingleton
class StatusSyncer(LocalSingletonBase):
	def sync(self):
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		
		try:
			all_users = user_provider.find_by_fqdn(component.host)
		except NotFoundException, e:
			return # No users yet
			
		for user in all_users:
			# We only need to send out a presence probe and forget; incoming responses will be 
			# handled by the default presence handler.
			user = user_provider.normalize_user(user)
			stanza = component.make_presence(ptype="probe", pto=user.jid, pfrom=component.boundjid)
			stanza.send()

@LocalSingleton
class VcardSyncer(LocalSingletonBase):
	def sync(self):
		# This re-generates the default vCard files for every user, to
		# reflect the data currently in the database for those users.
		user_provider = UserProvider.Instance(self.identifier)
		component = Component.Instance(self.identifier)
		logger = ApplicationLogger.Instance(self.identifier)
		configuration = ConfigurationProvider.Instance(self.identifier)
		
		with open(os.path.join(configuration.asset_path, "templates/vcard.dat"), "r") as template_file:
			template = template_file.read()
		
		try:
			all_users = user_provider.find_by_fqdn(component.host)
		except NotFoundException, e:
			return # No users yet
			
		for user in all_users:
			generated = template % {
				"first_name": user.first_name,
				"last_name": user.last_name, 
				"full_name": user.full_name,
				"mobile_number": user.phone_number,
				"email_address": user.email_address,
				"job_title": user.job_title,
				"nickname": user.nickname
			}
			
			username, fqdn = user.jid.split("@")
			fqdn_target = "/var/lib/prosody/%s/default_vcard" % prosody_quote(fqdn)
			target_path = "%s/%s.dat" % (fqdn_target, prosody_quote(username))
			
			try:
				os.makedirs(fqdn_target)
				
				for dirname, dirlist, filelist in os.walk("/var/lib/prosody/%s" % prosody_quote(fqdn)):
					# FIXME: This is suboptimal. Figure out a better way to fix perms.
					os.chmod(dirname, stat.S_IRWXG | stat.S_IRWXU)
			except OSError, e:
				# Directory already exists; this doesn't really matter, and we can
				# just ignore it.
				pass
			
			with open(target_path, "w") as f:
				f.write(generated)
				
			logger.debug("Regenerated vCard file for %s." % user.jid)

from .exceptions import NotFoundException
from .providers import UserProvider, PresenceProvider, AffiliationProvider, RoomProvider
from .component import Component
from .loggers import ApplicationLogger

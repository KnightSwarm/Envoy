from .util import Singleton, LocalSingleton, LocalSingletonBase, E, ET, cut_text

available_libraries = set()

try:
	import github
	from github.GithubException import UnknownObjectException as GithubUnknownObjectException
	available_libraries.add("github")
except Exception, e:
	pass

try:
	import trello
	from requests.exceptions import HTTPError as RequestsHTTPException
	available_libraries.add("trello")
except Exception, e:
	pass

try:
	import pyimgur
	available_libraries.add("pyimgur")
except Exception, e:
	pass

import requests, json # For other APIs that we don't have a library for
	
def require_library(name):
	if name not in available_libraries:
		raise LibraryUnavailableException("The URL could not be resolved, because the '%s' library is not installed." % name)

@LocalSingleton
class ImageResolver(LocalSingletonBase):
	def resolve_item(self, match, message, stanza):
		# IDEA: Serve permanent thumbnail from server, rather than just outputting the
		# original image with resizing parameters
		json = {
			"image": match["url"]
		}
		
		html = ET.tostring((
			E.img(src=match["url"])
		), method="html")
		
		return (html, json)
	
@LocalSingleton
class GitHubResolver(LocalSingletonBase):
	# FIXME: Nice name handling... Now some calls will throw "None" as name, if no realname is set.
	
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		configuration = ConfigurationProvider.Instance(self.identifier)
		try:
			require_library("github")
			self.client = github.MainClass.Github(configuration.github_token)
		except LibraryUnavailableException, e:
			pass
	
	def add_statistics(self, files):
		 # Calculates total additions, changes, and removals for a list of Files. Faster than a list comprehension.
		 # Changed lines are meaningless; it seems GitHub only does line-level diffing.
		additions = 0
		changes = 0
		deletions = 0
		
		for file_ in files:
			additions += file_.additions
			changes += file_.changes
			deletions += file_.deletions
			
		return (additions, changes, deletions)
	
	def resolve_user(self, match, message, stanza):
		# May also be organization
		require_library("github")
		
		# First try and see if this is an organization; GitHub also returns a 'user' for every organization.
		try:
			return self.resolve_organization(match, message, stanza)
		except GithubUnknownObjectException, e:
			pass # Not an organization
		
		# Retrieve it as a user
		try:
			user = self.client.get_user(match["user"])
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified user or organization does not exist.")
		
		if user.name is None:
			name = user.login
		else:
			name = "%s (%s)" % (user.name, user.login)
		
		description_blurbs = []
		
		if user.location is not None:
			description_blurbs.append("Lives in %s." % user.location)
		
		if user.company is not None:
			description_blurbs.append("Works at %s." % user.company)
			
		description = " ".join(description_blurbs)
				
		json = {
			"image": user.avatar_url,
			"title": name,
			"description": description,
			"statistics": "%s public repositories, %s public gists" % (user.public_repos, user.public_gists)
		}
		
		html = ET.tostring((
			E.div(
				E.img(src=user.avatar_url, class_="thumbnail"),
				E.div(name, class_="title"),
				E.div(description, class_="description"),
				E.div(
					E.strong(user.public_repos), " public repositories, ",
					E.strong(user.public_gists), " public gists.",
					class_="statistics"
				),
				class_="github-user"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_organization(self, match, message, stanza):
		# This is called by resolve_user to see if the given URL is an organization..
		# The resolve_user method will handle library exceptions occurring here.
		organization = self.client.get_organization(match["user"])
		
		if organization.name is None:
			name = organization.login
		else:
			name = "%s (%s)" % (organization.name, organization.login)
		
		description_blurbs = []
		
		if organization.location is not None:
			description_blurbs.append("Located in %s." % organization.location)
		
		if organization.blog is not None and organization.blog.strip() != "": # ???
			description_blurbs.append("Blog at %s." % organization.blog)
			
		description = " ".join(description_blurbs)
				
		json = {
			"image": organization.avatar_url,
			"title": name,
			"description": description,
			"statistics": "%s collaborators, %s followers, %s public repositories, %s public gists" % (organization.collaborators, organization.followers, organization.public_repos, organization.public_gists)
		}
		
		html = ET.tostring((
			E.div(
				E.div(name, class_="title"),
				E.div(description, class_="description"),
				E.div(
					E.strong(organization.collaborators), " collaborators, ",
					E.strong(organization.followers), " followers, ",
					E.strong(organization.public_repos), " public repositories, ",
					E.strong(organization.public_gists), " public gists.",
					class_="statistics"
				),
				class_="github-organization"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_repository(self, match, message, stanza):
		require_library("github")
		
		try:
			repo = self.client.get_repo("%s/%s" % (match["user"], match["repository"]))
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified repository does not exist or cannot be accessed.")
		
		json = {
			"title": repo.name,
			"description": repo.description,
			"statistics": "%s forks, %s followers, %s favourites" % (repo.forks_count, repo.watchers_count, repo.stargazers_count)
		}
		
		html = ET.tostring((
			E.div(
				E.div(repo.name, class_="title"),
				E.div(repo.description, class_="description"),
				E.div(
					E.strong(repo.forks_count), " forks, ",
					E.strong(repo.watchers_count), " followers, and ", # What the hell? Why is GitHub returning the Stargazer count for Watchers?
					E.strong(repo.stargazers_count), " favourites.",
					class_="statistics"
				),
				class_="github-repository"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_tree(self, match, message, stanza):
		# No information on directory trees is currently returned by the GitHub API; for now,
		# we will just return information about the branch.
		require_library("github")
		return self.resolve_branch(match, message, stanza)
		
	def resolve_branch(self, match, message, stanza):
		# Called by resolve_tree (temporarily).
		try:
			branch = self.client.get_repo("%s/%s" % (match["user"], match["repository"])).get_branch(match["branch"])
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified branch could not be found or accessed.")
		
		title = "Branch %s on %s/%s" % (branch.name, match["user"], match["repository"])
		
		json = {
			"title": title,
			"statistics": "Last commit: %s\n%s" % (branch.commit.sha, branch.commit.commit.message)
		}
		
		html = ET.tostring((
			E.div(
				E.div(title, class_="title"),
				E.div(
					"Last commit: ", E.strong(branch.commit.sha),
					E.div(branch.commit.commit.message, class_="message"),
					class_="statistics"
				),
				class_="github-branch"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_blob(self, match, message, stanza):
		# Not quite certain how to implement this. Returning branch information for now.
		require_library("github")
		return self.resolve_branch(match, message, stanza)
		
	def resolve_issue(self, match, message, stanza):
		require_library("github")
		
		try:
			issue = self.client.get_repo("%s/%s" % (match["user"], match["repository"])).get_issue(int(match["id"]))
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified issue could not be found.")
		
		name = "Issue #%d: %s" % (issue.number, issue.title)
		description = cut_text(issue.body, 250)
		
		json = {
			"title": name,
			"description": description,
			"statistics": "Status is '%s'. Opened by %s (%s)." % (issue.state, issue.user.name, issue.user.login)
		}
		
		html = ET.tostring((
			E.div(
				E.div(name, class_="title"),
				E.div(description, class_="description"),
				E.div(
					"Currently ", E.strong(issue.state), ". ",
					"Opened by ", E.strong(issue.user.name), " (%s)." % issue.user.login,
					class_="statistics"
				),
				class_="github-issue"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_pullrequest(self, match, message, stanza):
		require_library("github")
		
		try:
			pullreq = self.client.get_repo("%s/%s" % (match["user"], match["repository"])).get_pull(int(match["id"]))
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified pull request could not be found.")
		
		name = "Pull request #%d: %s" % (pullreq.number, pullreq.title)
		description = cut_text(pullreq.body, 250)
		
		json = {
			"title": name,
			"description": description,
			"statistics": "Status is '%s'. Opened by %s (%s). Results in %s line(s) added, %s deleted." % (pullreq.state, pullreq.user.name, pullreq.user.login, pullreq.additions, pullreq.deletions)
		}
		
		html = ET.tostring((
			E.div(
				E.div(name, class_="title"),
				E.div(description, class_="description"),
				E.div(
					"Currently ", E.strong(pullreq.state), ". ",
					"Opened by ", E.strong(pullreq.user.name), " (%s)." % pullreq.user.login,
					E.div(
						"Results in ",
						E.strong(pullreq.additions), " line(s) added, and ",
						E.strong(pullreq.deletions), " line(s) deleted.",
					),
					class_="statistics"
				),
				class_="github-pullreq"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_commit(self, match, message, stanza):
		require_library("github")
		
		try:
			commit = self.client.get_repo("%s/%s" % (match["user"], match["repository"])).get_commit(match["id"])
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified commit could not be found.")
		
		title = "Commit %s on %s/%s" % (commit.sha, match["user"], match["repository"])
		
		additions, changes, deletions = self.add_statistics(commit.files)
		
		json = {
			"title": title,
			"description": commit.commit.message,
			"statistics": "Committed by %s (%s). %s line(s) added, %s deleted." % (commit.committer.name, commit.committer.login, additions, deletions)
		}
		
		html = ET.tostring((
			E.div(
				E.div(title, class_="title"),
				E.div(
					"Committed by ", E.strong(commit.committer.name), " (%s)." % commit.committer.login,
					E.div(
						E.strong(additions), " line(s) added, ", E.strong(deletions), " line(s) deleted."
					),
					class_="statistics"
				),
				E.div(commit.commit.message, class_="description"),
				class_="github-commit"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_comparison(self, match, message, stanza):
		require_library("github")
		
		try:
			repo = self.client.get_repo("%s/%s" % (match["user"], match["repository"]))
			comparison = repo.compare(match["id1"], match["id2"])
			commit1 = comparison.base_commit
			commit2 = repo.get_commit(match["id2"]) # Not sure how to extract this from the comparison data...?
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified comparison could not be found.")
		
		title = "Comparison between %s and %s on %s/%s" % (commit1.sha, commit2.sha, match["user"], match["repository"])
		
		additions, changes, deletions = self.add_statistics(comparison.files)
		
		json = {
			"title": title,
			"statistics": "%s line(s) added, %s deleted." % (additions, deletions)
		}
		
		html = ET.tostring((
			E.div(
				E.div(title, class_="title"),
				E.div(
					E.strong(additions), " line(s) added, ", E.strong(deletions), " line(s) deleted.",
					class_="statistics"
				),
				class_="github-comparison"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_gist_user(self, match, message, stanza):
		# For now, we'll just let it resolve the regular GitHub user. That will give us gist stats as well.
		require_library("github")
		return self.resolve_user(match, message, stanza)
		
	def resolve_gist(self, match, message, stanza):
		require_library("github")
		
		try:
			gist = self.client.get_gist(match["id"])
		except GithubUnknownObjectException, e:
			raise ResolutionFailedException("The specified gist does not exist or cannot be accessed.")
		
		name = "Gist #%s" % gist.id
		
		json = {
			"title": name,
			"description": gist.description,
			"statistics": "Created by %s (%s)" % (gist.user.name, gist.user.login)
		}
		
		html = ET.tostring((
			E.div(
				E.div(name, class_="title"),
				E.div(gist.description, class_="description"),
				E.div(
					"Created by ", E.strong(gist.user.name), " (%s)." % (gist.user.login),
					class_="statistics"
				),
				class_="github-gist"
			)
		), method="html")
		
		return (html, json)
		
@LocalSingleton
class ImgurResolver(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		configuration = ConfigurationProvider.Instance(self.identifier)
		try:
			require_library("pyimgur")
			self.client = pyimgur.Imgur(configuration.imgur_client_id)
		except LibraryUnavailableException, e:
			pass
			
	def process_image(self, image):
		# Turns an Image object (or derivative thereof such as GalleryImage) into HTML/JSON
		if image.title is None:
			title = "Untitled"
		else:
			title = image.title
		
		json = {
			"title": title,
			"image": image.link_small_thumbnail
		}
		
		html = ET.tostring((
			E.div(
				E.div(title, class_="title"),
				E.img(src=image.link_small_thumbnail),
				class_="imgur-image"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_item(self, match, message, stanza):
		# May also be false positive
		# IDEA: Use ImageResolver for thumbnail
		require_library("pyimgur")
		try:
			return self.process_image(self.client.get_image(match["id"]))
		except Exception, e: # WTF pyimgur, why no clear custom exceptions?
			raise ResolutionFailedException("Could not resolve the specified Imgur image.")
		
	def resolve_gallery_item(self, match, message, stanza):
		# IDEA: Use ImageResolver for thumbnail
		require_library("pyimgur")
		try:
			return self.process_image(self.client.get_gallery_image(match["id"]))
		except Exception, e:
			raise ResolutionFailedException("Could not resolve the specified Imgur image.")

@LocalSingleton
class BeanstalkResolver(LocalSingletonBase):
	# IDEA: Support parsing links of other organizations that the configured account has
	# access to? This might not be desirable, from a privacy/security point-of-view.
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		configuration = ConfigurationProvider.Instance(self.identifier)
		
		# Apparently the canonical Beanstalk API library for Python (https://github.com/sherzberg/python-beanstalk-api)
		# uses global state, and keeps its authentication details as a singleton. That makes it useless for our purposes;
		# after all, we want to be able to manage authentication for several separate FQDNs at a time.
		# I-Can't-Believe-It's-Not-Duct-Tape solution: we'll use the `requests` library directly.
		self.base_domain = "https://%s.beanstalkapp.com" % configuration.beanstalk_host
		self.host = configuration.beanstalk_host
		self.client = requests.Session()
		self.client.raise_for_status = True
		self.client.auth = (configuration.beanstalk_user, configuration.beanstalk_key)
		self.client.headers.update({
			"user-agent": "Envoy HTML Preview Resolver (https://github.com/KnightSwarm/Envoy)",
			"content-type": "application/json"
		})
		
	def find_repository_by_name(self, name):
		repositories = self.client.get(self.base_domain + "/api/repositories.json").json()
		repository = None
		
		for option in repositories:
			if option["repository"]["name"] == name:
				repository = option["repository"]
				
		if repository is None:
			raise ResolutionFailedException("No such repository exists.")
			
		return repository
	
	def resolve_repository(self, match, message, stanza):
		if match["organization"] == self.host:
			repository = self.find_repository_by_name(match["repository"])
				
			json = {
				"title": "%s (%s)" % (repository["title"], repository["name"]),
				"statistics": "VCS used is %s." % repository["vcs"]
			}
			
			html = ET.tostring((
				E.div(
					E.div("%s (%s)" % (repository["title"], repository["name"]), class_="title"),
					E.div(
						"A ", E.strong(repository["vcs"]), " repository.",
						class_="statistics"
					),
					class_="beanstalk-repository"
				)
			), method="html")
			
			return (html, json)
		else:
			raise ResolutionFailedException("Referenced repository does not belong to configured organization/host.")
	
	def resolve_changeset(self, match, message, stanza):
		if match["organization"] == self.host:
			repository = self.find_repository_by_name(match["repository"])
			
			response = self.client.get(self.base_domain + "/api/changesets/%s.json" % match["id"], params={"repository_id": repository["id"]})
			
			try: # Apparently Beanstalk API responses are incredibly slow for unknown changesets. Not sure what that's all about.
				response.raise_for_status()
			except RequestsHTTPException, e:
				raise ResolutionFailedException("No such changeset found.")
			
			changeset = response.json()["revision_cache"]
			
			if changeset["hash_id"] is not None:
				title = "Commit %s on %s (%s)" % (changeset["hash_id"], repository["title"], repository["name"])
			else:
				title = "Revision %s on %s (%s)" % (changeset["revision"], repository["title"], repository["name"])
			
			json = {
				"title": title,
				"description": changeset["message"],
				"statistics": "Committed by %s (%s) at %s." % (changeset["author"], changeset["email"], changeset["time"])
			}
			
			html = ET.tostring((
				E.div(
					E.div(title, class_="title"),
					E.div(
						"Committed by ", E.strong(changeset["author"]), " (%s)" % changeset["email"],
						", at", E.strong(changeset["time"]), ".",
						class_="statistics"
					),
					E.div(changeset["message"], class_="description"),
					class_="beanstalk-changeset"
				)
			), method="html")
				
			return (html, json)
		else:
			raise ResolutionFailedException("Referenced repository does not belong to configured organization/host.")
	
@LocalSingleton
class TrelloResolver(LocalSingletonBase):
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		configuration = ConfigurationProvider.Instance(self.identifier)
		try:
			require_library("trello")
			self.client = trello.TrelloApi(configuration.trello_key, token=configuration.trello_token)
		except LibraryUnavailableException, e:
			pass
			
	def resolve_board(self, match, message, stanza):
		require_library("trello")
		
		try:
			board = self.client.boards.get(match["id"])
		except RequestsHTTPException, e:
			raise ResolutionFailedException("The specified board does not exist or cannot be accessed.")
		
		organization = self.client.organizations.get(board["idOrganization"])
		
		json = {
			"title": board["name"],
			"description": board["desc"],
			"statistics": "Owned by %s" % organization['displayName']
		}
		
		html = ET.tostring((
			E.div(
				E.div(board["name"], class_="title"),
				E.div(board["desc"], class_="description"),
				E.div(
					"Owned by ", E.strong(organization["displayName"]), ".",
					class_="statistics"
				),
				class_="trello-board"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_card(self, match, message, stanza):
		require_library("trello")
		
		try:
			card = self.client.cards.get(match["id"])
		except RequestsHTTPException, e:
			raise ResolutionFailedException("The specified card does not exist or cannot be accessed.")
		
		board = self.client.boards.get(card["idBoard"])
		organization = self.client.organizations.get(board["idOrganization"])
		
		json = {
			"title": card["name"],
			"description": card["desc"],
			"statistics": "On board %s, owned by %s" % (board["name"], organization['displayName'])
		}
		
		html = ET.tostring((
			E.div(
				E.div(card["name"], class_="title"),
				E.div(card["desc"], class_="description"),
				E.div(
					"On board ", E.strong(board["name"]), ", ",
					"owned by ", E.strong(organization["displayName"]), ".",
					class_="statistics"
				),
				class_="trello-card"
			)
		), method="html")
		
		return (html, json)
		
	def resolve_user(self, match, message, stanza):
		# May also be organization or false positive
		require_library("trello")
		
		try:
			organization = self.client.organizations.get(match["id"])
			return self.process_organization(organization, match, message, stanza)
		except RequestsHTTPException, e:
			# If not an organization, it might be a user.
			try:
				user = self.client.members.get(match["id"])
				return self.process_user(user, match, message, stanza)
			except RequestsHTTPException, e:
				raise ResolutionFailedException("No such user or organization was found.")
				
	def process_organization(self, organization, match, message, stanza):
		# Called by resolve_user if the specified ID belonged to an organization.
		json = {
			"title": organization["displayName"],
			"description": organization["desc"],
		}
		
		html = ET.tostring((
			E.div(
				E.div(organization["displayName"], class_="title"),
				E.div(organization["desc"], class_="description"),
				class_="trello-organization"
			)
		), method="html")
		
		return (html, json)
				
	def process_user(self, user, match, message, stanza):
		# Called by resolve_user if the specified ID belonged to a user.
		if user["bio"] is None:
			description = ""
		else:
			description = user["bio"]
		
		json = {
			"title": "%s (%s)" % (user["fullName"], user["username"]),
			"description": description
		}
		
		html = ET.tostring((
			E.div(
				E.div(user["fullName"], " (%s)" % user["username"], class_="title"),
				E.div(description, class_="description"),
				class_="trello-user"
			)
		), method="html")
		
		return (html, json)

from .exceptions import LibraryUnavailableException, ResolutionFailedException
from .providers import ConfigurationProvider

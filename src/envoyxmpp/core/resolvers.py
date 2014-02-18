from .util import Singleton, LocalSingleton, LocalSingletonBase, E, ET

available_libraries = set()

try:
	import github
	from github.GithubException import UnknownObjectException as GithubUnknownObjectException
	available_libraries.add("github")
except:
	pass

try:
	import libsaas
	available_libraries.add("libsaas")
except:
	pass
	
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
	def __init__(self, singleton_identifier=None):
		self.identifier = singleton_identifier
		configuration = ConfigurationProvider.Instance(self.identifier)
		try:
			require_library("github")
			self.client = github.MainClass.Github(configuration.github_token)
		except LibraryUnavailableException, e:
			pass
	
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
		# This is called by resolve_user if the given URL does not contain a user.
		# The resolve_user method will also handle library exceptions occurring here.
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
			"title": "%s" % repo.name,
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
		require_library("github")
		pass
		
	def resolve_blob(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_issue(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_pullrequest(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_commit(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_comparison(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_gist_user(self, match, message, stanza):
		require_library("github")
		pass
		
	def resolve_gist(self, match, message, stanza):
		require_library("github")
		pass	
	
@LocalSingleton
class ImgurResolver(LocalSingletonBase):
	def resolve_item(self, match, message, stanza):
		# May also be false positive
		# IDEA: Use ImageResolver for thumbnail
		pass
	
	def resolve_gallery_item(self, match, message, stanza):
		# IDEA: Use ImageResolver for thumbnail
		pass
	
@LocalSingleton
class BeanstalkResolver(LocalSingletonBase):
	def resolve_organization(self, match, message, stanza):
		pass
	
	def resolve_repository(self, match, message, stanza):
		pass
	
	def resolve_changeset(self, match, message, stanza):
		pass
	
	def resolve_path(self, match, message, stanza):
		# The 'type' match may refer to the 'git' string (for Git repositories) or an SVN subdirectory (trunk/tags/etc.)
		pass
	
@LocalSingleton
class TrelloResolver(LocalSingletonBase):
	def resolve_board(self, match, message, stanza):
		require_library("libsaas")
		pass
		
	def resolve_card(self, match, message, stanza):
		require_library("libsaas")
		pass
		
	def resolve_user(self, match, message, stanza):
		# May also be organization or false positive
		require_library("libsaas")
		pass

from .exceptions import LibraryUnavailableException, ResolutionFailedException
from .providers import ConfigurationProvider

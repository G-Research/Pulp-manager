"""Methods for interacting with repositories
"""

import re
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources.repository import (
    Repository, FileRepository, RpmRepository, DebRepository, PythonRepository, ContainerRepository,
    FileRepositoryVersion, RpmRepositoryVersion, DebRepositoryVersion, PythonRepositoryVersion,
     ContainerRepositoryVersion
)
from .tasks import get_task, monitor_task


REPO_INVALID_CREATOIN_FIELDS = [
    'pulp_href', 'pulp_created', 'versions_href', 'latest_version_href'
]
BASE_URL = '/repositories/'
REPO_TYPE_URL = {
    'file': '{0}file/file/'.format(BASE_URL),
    'rpm': '{0}rpm/rpm/'.format(BASE_URL),
    'deb': '{0}deb/apt/'.format(BASE_URL),
    'python': '{0}python/python/'.format(BASE_URL),
    'container': '{0}container/container/'.format(BASE_URL),
}


def remove_invalid_creation_fields(repo: Repository):
    """Removes the fields that aren't valid for the creation/updating
    of a Repository object and returns a dict with the fields that can
    be used for the body
    :param repo: Repository to remove the fields from
    :type repo: Repository
    :return: dict
    """

    params = repo.dict(exclude_unset=True)
    for field in REPO_INVALID_CREATOIN_FIELDS:
        if field in params:
            del params[field]

    return params


def get_repo_class(repo_type: str):
    """Returns the class type of the repo given the repo type name
    :param repo_type: Name of repo type to get class for
    :type repo_type: str
    :return: Repository
    """

    repository_class = None
    if repo_type == 'file':
        repository_class = FileRepository
    elif repo_type == 'rpm':
        repository_class = RpmRepository
    elif repo_type == 'deb':
        repository_class = DebRepository
    elif repo_type == 'python':
        repository_class = PythonRepository
    elif repo_type == 'container':
        repository_class = ContainerRepository

    if repository_class:
        return repository_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given repo type. Supported types: {0}".format(
            ', '.join(REPO_TYPE_URL.keys())
        )
    )


def get_repo_version_class(repo_type: str):
    """Returns the class type of the repo version given the repo version
    type name
    :param repo_type: Name of repo type to get class for
    :type repo_type: str
    :return: RepositoryVersion
    """

    repository_version_class = None
    if repo_type == 'file':
        repository_version_class = FileRepositoryVersion
    elif repo_type == 'rpm':
        repository_version_class = RpmRepositoryVersion
    elif repo_type == 'deb':
        repository_version_class = DebRepositoryVersion
    elif repo_type == 'python':
        repository_version_class = PythonRepositoryVersion
    elif repo_type == 'container':
        repository_version_class = ContainerRepositoryVersion

    if repository_version_class:
        return repository_version_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given repo type. Supported types: {0}".format(
            ', '.join(REPO_TYPE_URL.keys())
        )
    )


def get_all_repos(client: Pulp3Client, repo_type: str=None, params: dict=None):
    """Retrieves all repositories
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo_type: Limits the type of repo to reutnr e.g. rpm
    :type repo_type: str
    :param params: dict of arguments to use to filter repos to return
    :type params: dict
    :return: List of repositories
    """

    url = BASE_URL
    repository_type = Repository

    if repo_type and repo_type in REPO_TYPE_URL:
        url = REPO_TYPE_URL[repo_type]
        repository_type = get_repo_class(repo_type)
    elif repo_type:
        raise PulpV3InvalidArgumentError(
            "Client does not support given repo type. Supported types: {0}".format(
                ', '.join(REPO_TYPE_URL.keys())
            )
        )

    repositories = client.get_page_results(url, params=params)
    return parse_obj_as(List[repository_type], repositories)


def get_repo(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified repo from the given href

    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the repo to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Repository or None
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a repository')

    match = re.match('/pulp/api/v3/repositories/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        repo_type = match.groups()[0]
        repository_class = get_repo_class(repo_type)
        result = client.get(href, params)
        return repository_class(**result)

    raise PulpV3InvalidArgumentError(
        "Unable to identify repository type for href {0}".format(href)
    )


def get_all_repo_versions(client: Pulp3Client, href: str, params: dict=None):
    """Gets all the versions of the specified repo

    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the repo to get versions for
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: List RepoVersion
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a repository')

    if 'versions/' not in href:
        PulpV3InvalidArgumentError('href is not for a repository version')

    match = re.match('/pulp/api/v3/repositories/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        url = href
        if not url.endswith('/'):
            url += '/'

        url += 'versions/'

        repo_type = match.groups()[0]
        repository_version_class = get_repo_version_class(repo_type)
        get_repo(client, href)
        repository_versions = client.get_page_results(url, params=params)
        return parse_obj_as(List[repository_version_class], repository_versions)

    raise PulpV3InvalidArgumentError(
        "Unable to identify repository version type for href {0}".format(href)
    )


def get_repo_version(client: Pulp3Client, href: str, params: dict=None):
    """Returns the specified repo version

    :param client: Instace of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the repo version to get
    :type href: str
    :param params: dict of params to use to filter fields
    :type params: dict
    :return: RepoVersion
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a repository')

    if not href.endswith('/'):
        href += '/'

    if not href.endswith('versions/'):
        PulpV3InvalidArgumentError('href is not for a repository version')

    match = re.match('/pulp/api/v3/repositories/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        repo_type = match.groups()[0]
        repository_version_class = get_repo_version_class(repo_type)
        result = client.get(href, params)
        return repository_version_class(**result)

    raise PulpV3InvalidArgumentError(
        "Unable to identify repository version type for href {0}".format(href)
    )


def new_repo(client: Pulp3Client, repo: Repository):
    """Creates a new instance of the given repo
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to create
    :type repo: Repository
    :return: Newly created repository
    """

    if not isinstance(repo, Repository):
        raise PulpV3InvalidArgumentError(
            "repo is not of type Repository got {0}".format(type(repo))
        )

    params = remove_invalid_creation_fields(repo)
    repo_type = None

    if isinstance(repo, FileRepository):
        repo_type = 'file'
    elif isinstance(repo, RpmRepository):
        repo_type = 'rpm'
    elif isinstance(repo, DebRepository):
        repo_type = 'deb'
    elif isinstance(repo, PythonRepository):
        repo_type = 'python'
    elif isinstance(repo, ContainerRepository):
        repo_type = 'container'
    else:
        raise PulpV3InvalidArgumentError(
            "Client does not support given repo type. Supported types: {0}".format(
                ', '.join(REPO_TYPE_URL.keys())
            )
        )

    url = REPO_TYPE_URL[repo_type]
    result = client.post(url, params)
    repo.update(result)


def update_repo(client: Pulp3Client, repo: Repository):
    """Updates an existing repo and returns the task object
    for monitoring progress
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to update
    :type repo: Repository
    :return: Task
    """

    if not isinstance(repo, Repository):
        raise PulpV3InvalidArgumentError(
            "repo is not of type Repository got {0}".format(type(repo))
        )

    href = repo.pulp_href
    params = remove_invalid_creation_fields(repo)
    result = client.patch(href, params)
    return get_task(client, result['task'])


def update_repo_monitor(client: Pulp3Client, repo: Repository, poll_interval_sec: int = 15,
        max_wait_count: int = 200, error: bool = True):
    """Updates an existing repo and monitors the task for complete. Once completed
    returns and updated repository object
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to update
    :type repo: Repository
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Repository
    """

    href = repo.pulp_href
    task = update_repo(client, repo)
    monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    updated_repo = get_repo(client, href)
    repo.update(updated_repo.dict())


def copy_repo(client: Pulp3Client, source_repo: Repository, dest_repo: Repository,
        structured=True):
    """Copies the latest repository version from the source_repo to the dest_repo

    :param source_repo: Source repository to copy
    :type source_repo: Repository
    :param dest_repo: Destination repository to copy to
    :type dest_repo: Repository
    :param structured: Only used for deb repos.Also copy any distributions, components, and
                       releases as needed for any packages being copied. This will allow for
                       structured publications of the target repository.Default is set to True
    :type structured: bool
    :return: Task
    """

    #pylint: disable=unidiomatic-typecheck
    if type(source_repo) != type(dest_repo):
        raise PulpV3InvalidArgumentError(
            "Source is of type {0} and dest repo is {1}. Source and dest must be the same".format(
                type(source_repo), type(dest_repo)
            )
        )

    if not isinstance(source_repo, RpmRepository) and not isinstance(source_repo, DebRepository):
        raise PulpV3InvalidArgumentError(
            "Only RpmRepository of DebRepository is supported for copy. Source repo: {0}".format(
                type(source_repo)
            )
        )

    body = {
        'config': [{
            'source_repo_version': source_repo.latest_version_href,
            'dest_repo': dest_repo.pulp_href
        }]
    }

    url = '/rpm/copy/'
    if isinstance(source_repo, DebRepository):
        body['structured'] = structured
        url = '/deb/copy/'

    result = client.post(url, body)
    return get_task(client, result['task'])


def copy_repo_monitor(client: Pulp3Client, source_repo: Repository, dest_repo: Repository,
        structured: bool = True, poll_interval_sec: int = 15, max_wait_count: int = 200,
        error: bool = True):
    """Copies the latest repository version from the source_repo to the dest_repo

    :param source_repo: Source repository to copy
    :type source_repo: Repository
    :param dest_repo: Destination repository to copy to
    :type dest_repo: Repository
    :param structured: Only used for deb repos.Also copy any distributions, components, and
                       releases as needed for any packages being copied. This will allow for
                       structured publications of the target repository.Default is set to True
    :type structured: bool
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = copy_repo(client, source_repo, dest_repo, structured)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)


def modify_repo(client: Pulp3Client, repo: Repository, base_version: str,
        add_content_units: List[str] = None, remove_content_units: List[str] = None):
    """Triggers an asynchronous task to create a new repository version. Returns task object
    that can be used for monitoring progress
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to modify and create a new version for
    :type repo: Repository
    :param base_version: A repository version href whose content will be used as the initial set
                         of content for the new repository version
    :type base_version: str
    :param add_content_units: A list of content units (href) to add to a new repository version.
                              This content is added after remove_content_units are removed.
    :type add_content_units: List[str]
    :param remove_content_units: A list of content units (hrefs) to remove from the latest
                                 repository version. You may also specify '*' as an entry to remove
                                 all content. This content is removed before add_content_units are
                                 added.
    :type remove_content_units: List[str]
    :return: Task
    """

    if not isinstance(repo, Repository):
        raise PulpV3InvalidArgumentError(
            "repo is not of type Repository got {0}".format(type(repo))
        )

    supported_repo_types = ['file', 'rpm', 'deb', 'python']

    match = re.match('/pulp/api/v3/repositories/([a-z]+)/', repo.pulp_href)
    if match and len(match.groups()) > 0:
        repo_type = match.groups()[0]
        if repo_type not in supported_repo_types:
            raise PulpV3InvalidArgumentError(
                ("The client currently only supports modify on repos of type {0}. Check with pulp "
                 "API to see if can be extended").format(', '.join(supported_repo_types))
            )
    else:
        raise PulpV3InvalidArgumentError(
            "Invalid href given not matching pattern /pulp/api/v3/repositories/([a-z]+)/"
        )

    if ((not add_content_units or len(add_content_units) == 0) and
            not remove_content_units or len(remove_content_units) == 0):
        raise PulpV3InvalidArgumentError(
            "At least one of add_content_units or remove_content_units must be specified"
        )

    modify_url = repo.pulp_href
    if not modify_url.endswith('/'):
        modify_url += '/'
    modify_url += 'modify/'

    body = {'base_version': base_version}

    if add_content_units:
        body['add_content_units'] = add_content_units
    if remove_content_units:
        body['remove_content_units'] = remove_content_units

    result = client.post(modify_url, body)
    return get_task(client, result['task'])


def modify_repo_monitor(client: Pulp3Client, repo: Repository, base_version: str,
        add_content_units: List[str] = None, remove_content_units: List[str] = None,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Triggers an asynchronous task to create a new repository version. Returns the Task object
    monitoring has completed. This is due to it not being guranteed a new repo version will be
    created. So checks of the task result are required
    repo version
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to modify and create a new version for
    :type repo: Repository
    :param base_version: A repository version href whose content will be used as the initial set
                         of content for the new repository version
    :type base_version: str
    :param add_content_units: A list of content units (href) to add to a new repository version.
                              This content is added after remove_content_units are removed.
    :type add_content_units: List[str]
    :param remove_content_units: A list of content units (hrefs) to remove from the latest
                                 repository version. You may also specify '*' as an entry to remove
                                 all content. This content is removed before add_content_units are
                                 added.
    :type remove_content_units: List[str]
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = modify_repo(client, repo, base_version, add_content_units, remove_content_units)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)


def sync_repo(client: Pulp3Client, repo: Repository, body: dict):
    """Sync the specified repo in pulp. Unfortunately the different repos have different
    sync options, so the body of params for the sync needs to be specified. If the
    repo is linked to a remote, then an empty dict can be posted for a series of default
    options to be used. Returns object to use for monitoring
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to sync
    :type repo: Repository
    :param body: Dict of params to send for the sync
    :type body: dict
    :return: Task
    """

    if not isinstance(repo, Repository):
        raise PulpV3InvalidArgumentError(
            "repo is not of type Repository got {0}".format(type(repo))
        )

    sync_url = repo.pulp_href
    if not sync_url.endswith('/'):
        sync_url += '/'
    sync_url += 'sync/'

    result = client.post(sync_url, body)
    return get_task(client, result['task'])


def sync_repo_monitor(client: Pulp3Client, repo: Repository, body: dict,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error=True):
    """Sync the specified repo in pulp. Unfortunately the different repos have different
    sync options, so the body of params for the sync needs to be specified. If the
    repo is linked to a remote, then an empty dict can be posted for a series of default
    options to be used
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: Repository to sync
    :type repo: Repository
    :param body: Dict of params to send for the sync
    :type body: dict
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = sync_repo(client, repo, body)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)


def delete_repo(client: Pulp3Client, repo: Repository):
    """Deletes the request repo and reutrns the task object
    for monitoring
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo: repo to delete
    :type repo: Repository
    :return: Task
    """

    if not isinstance(repo, Repository):
        raise PulpV3InvalidArgumentError(
            "repo is not of type Repository got {0}".format(type(repo))
        )

    result = client.delete(repo.pulp_href)
    return get_task(client, result['task'])


def delete_repo_monitor(client: Pulp3Client, repo: Repository, poll_interval_sec: int = 15,
         max_wait_count: int = 200, error: bool = True):
    """Deletes the requested repo and monitors the task for completed. Returns the Task
    object on completion
    :param client: Client to connect to the API with
    :type client: Pulp3Client
    :param repo: Repository to delete
    :type repo: Repository
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = delete_repo(client, repo)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)

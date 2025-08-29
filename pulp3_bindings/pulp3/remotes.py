"""Methods for interacting with remotesitories
"""

import re
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources import (
    Remote, FileRemote, RpmRemote, DebRemote, PythonRemote, ContainerRemote
)
from .tasks import get_task, monitor_task


REMOTE_INVALID_CREATION_FIELDS = [
    'pulp_href', 'pulp_created', 'versions_href', 'hidden_fields', 'pulp_last_updated'
]
BASE_URL = '/remotes/'
REMOTE_TYPE_URL = {
    'file': '{0}file/file/'.format(BASE_URL),
    'rpm': '{0}rpm/rpm/'.format(BASE_URL),
    'deb': '{0}deb/apt/'.format(BASE_URL),
    'python': '{0}python/python/'.format(BASE_URL),
    'container': '{0}container/container/'.format(BASE_URL),
}


def remove_invalid_creation_fields(remote: Remote):
    """Removes the fields that aren't valid for the creation/updating
    of a Remote object and returns a dict with the fields that can
    be used for the body
    :param remote: Remote to remove the fields from
    :type remote: Remote
    :return: dict
    """

    params = remote.dict(exclude_unset=True)
    for field in REMOTE_INVALID_CREATION_FIELDS:
        if field in params:
            del params[field]

    # header isn't allowed to be posted as null
    if 'headers' in params and params['headers'] is None:
        del params['headers']

    # ensure that we don't overwrite/remove hidden fields
    # that have been set. Check if emtpy string has been set
    # and if so use that as a way to clear
    # This won't be set if createing a new repo
    if remote.hidden_fields:
        for hidden_field in remote.hidden_fields:
            if hidden_field.name in params and params[hidden_field.name] is None:
                del params[hidden_field.name]
            elif hidden_field.name in params and params[hidden_field.name] == '':
                params[hidden_field.name] = None # Will clear value
    return params


def get_remote_class(remote_type: str):
    """Returns the class type of the remote given the remote type name
    :param remote_type: Name of remote type to get class for
    :type remote_type: str
    :return: Remote
    """

    remote_class = None
    if remote_type == 'file':
        remote_class = FileRemote
    elif remote_type == 'rpm':
        remote_class = RpmRemote
    elif remote_type == 'deb':
        remote_class = DebRemote
    elif remote_type == 'python':
        remote_class = PythonRemote
    elif remote_type == 'container':
        remote_class = ContainerRemote

    if remote_class:
        return remote_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given remote type. Supported types: {0}".format(
            ', '.join(REMOTE_TYPE_URL.keys())
        )
    )


def get_all_remotes(client: Pulp3Client, remote_type: str=None, params: dict=None):
    """Retrieves all remotes
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param remote_type: Limits the type of remote to returbn e.g. rpm
    :type remote_type: str
    :param params: dict of arguments to use to filter remotes to return
    :type params: dict
    :return: List of remotes
    """

    url = BASE_URL
    remote_class = Remote

    if remote_type is not None and remote_type in REMOTE_TYPE_URL:
        url = REMOTE_TYPE_URL[remote_type]
        remote_class = get_remote_class(remote_type)
    elif remote_type is not None:
        raise PulpV3InvalidArgumentError(
            "Client does not support given remote type {0}. Supported types: {1}".format(
                remote_type, ', '.join(REMOTE_TYPE_URL.keys())
            )
        )

    remotes = client.get_page_results(url, params=params)
    return parse_obj_as(List[remote_class], remotes)


def get_remote(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified remote from the given href
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the remote to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Remote or None
    """

    if BASE_URL not in href:
        raise PulpV3InvalidArgumentError('href is not to a remote')

    match = re.match('/pulp/api/v3/remotes/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        remote_type = match.groups()[0]
        remote_class = get_remote_class(remote_type)
        result = client.get(href, params)
        return remote_class(**result)

    raise PulpV3InvalidArgumentError('href did not match pattern /pulp/api/v3/remotes/([a-z]+)/')

def new_remote(client: Pulp3Client, remote: Remote):
    """Commits the new remote to the database and updates the
    remote object that was passed through
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param remote: Remote to create
    :type remote: Remote
    :return: Newly created remote
    """

    if not isinstance(remote, Remote):
        raise PulpV3InvalidArgumentError("Expected type Remote got {0}".format(type(remote)))

    # Some extra args need removing for a valid post
    # which is why exclude_unset is not used here
    params = remove_invalid_creation_fields(remote)
    remote_type =  None

    if isinstance(remote, FileRemote):
        remote_type = 'file'
    elif isinstance(remote, RpmRemote):
        remote_type = 'rpm'
    elif isinstance(remote, DebRemote):
        remote_type = 'deb'
    elif isinstance(remote, PythonRemote):
        remote_type = 'python'
    elif isinstance(remote, ContainerRemote):
        remote_type = 'container'
    else:
        raise PulpV3InvalidArgumentError(
            "Client does not support given remote type. Supported types: {0}".format(
                ', '.join(REMOTE_TYPE_URL.keys())
            )
        )

    url = REMOTE_TYPE_URL[remote_type]
    result = client.post(url, params)
    remote.update(result)


def update_remote(client: Pulp3Client, remote: Remote):
    """Updates an existing remote and returns the task object
    for monitoring progress
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param remote: Remote to update
    :type remote: Remote
    :return: Task
    """

    if not isinstance(remote, Remote):
        raise PulpV3InvalidArgumentError("Expected type Remote got {0}".format(type(remote)))

    href = remote.pulp_href
    params = remove_invalid_creation_fields(remote)
    result = client.patch(href, params)
    return get_task(client, result['task'])


def update_remote_monitor(client: Pulp3Client, remote: Remote, poll_interval_sec: int = 15,
        max_wait_count: int = 200, error: bool = True):
    """Updates an existing remote and monitors the task for complete. Once completed
    updates the remote object that was passed through
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param remote: Remote to update
    :type remote: Remote
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Remote
    """

    task = update_remote(client, remote)
    monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    updated_remote = get_remote(client, remote.pulp_href)
    remote.update(updated_remote.dict())


def delete_remote(client: Pulp3Client, remote: Remote):
    """Deletes the request remote and reutrns the task object
    for monitoring
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param remote: remote to delete
    :type remote: Remote
    :return: Task
    """

    if not isinstance(remote, Remote):
        raise PulpV3InvalidArgumentError("Expected type Remote got {0}".format(type(remote)))

    result = client.delete(remote.pulp_href)
    return get_task(client, result['task'])


def delete_remote_monitor(client: Pulp3Client, remote: Remote, poll_interval_sec: int = 15,
         max_wait_count: int = 200, error: bool = True):
    """Deletes the requested remote and monitors the task for completed. Returns the Task
    object on completion
    :param client: Client to connect to the API with
    :type client: Pulp3Client
    :param remote: Remote to delete
    :type remote: Remote
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = delete_remote(client, remote)
    task = monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    return task

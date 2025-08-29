"""Methods for interacting with publications
"""

import re
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources.publication import (
    Publication, FilePublication, RpmPublication, DebPublication, PythonPublication
)
from .tasks import get_task, monitor_task


PUBLICATION_INVALID_CREATION_FIELDS = [
    'pulp_href', 'pulp_created'
]
BASE_URL = '/publications/'
PUBLICATION_TYPE_URL = {
    'file': '{0}file/file/'.format(BASE_URL),
    'rpm': '{0}rpm/rpm/'.format(BASE_URL),
    'deb': '{0}deb/apt/'.format(BASE_URL),
    'python': '{0}python/pypi/'.format(BASE_URL)
}


def remove_invalid_creation_fields(publication: Publication):
    """Removes the fields that aren't valid for the creation/updating
    of a Remote object and returns a dict with the fields that can
    be used for the body
    :param publication: Publication to remove the fields from
    :type publication: Publication
    :return: dict
    """

    params = publication.dict(exclude_unset=True)
    for field in PUBLICATION_INVALID_CREATION_FIELDS:
        if field in params:
            del params[field]

    # Either allowed repository or repository_version not both
    if 'repository' in params and 'repository_version' in params:
        raise PulpV3InvalidArgumentError(
            "Only repository or repository_version can be specified. Not both"
        )

    return params


def get_publication_class(publication_type: str):
    """Returns the class type of the pubication given the publication type name
    :param publication_type: Name of publication type to get class for
    :type publication_type: str
    :return: Publication
    """

    publication_class = None
    if publication_type == 'file':
        publication_class = FilePublication
    elif publication_type == 'rpm':
        publication_class = RpmPublication
    elif publication_type == 'deb':
        publication_class = DebPublication
    elif publication_type == 'python':
        publication_class = PythonPublication

    if publication_class:
        return publication_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given publication type. Supported types: {0}".format(
            ', '.join(PUBLICATION_TYPE_URL.keys())
        )
    )


def get_all_publications(client: Pulp3Client, publication_type: str=None, params: dict=None):
    """Retrieves all publications
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param publication_type: Limits the type of publication to return e.g. rpm
    :type publication_type: str
    :param params: dict of arguments to use to filter publications to return
    :type params: dict
    :return: List of publications
    """

    url = BASE_URL
    publication_class = Publication

    if publication_type is not None and publication_type in PUBLICATION_TYPE_URL:
        url = PUBLICATION_TYPE_URL[publication_type]
        publication_class = get_publication_class(publication_type)
    elif publication_type is not None:
        raise PulpV3InvalidArgumentError(
            "Client does not support given publication type {0}. Supported types: {1}".format(
                publication_type, ', '.join(PUBLICATION_TYPE_URL.keys())
            )
        )

    publications = client.get_page_results(url, params=params)
    return parse_obj_as(List[publication_class], publications)


def get_publication(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified publication from the given href
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the publication to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Publication
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a publication')

    match = re.match('/pulp/api/v3/publications/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        publication_type = match.groups()[0]
        publication_class = get_publication_class(publication_type)
        result = client.get(href, params)
        return publication_class(**result)

    raise PulpV3InvalidArgumentError(
        "href does not match pattern /pulp/api/v3/publications/([a-z]+)/"
    )


def new_publication(client: Pulp3Client, publication: Publication):
    """Creates a new instance of the given publication. Returns
    Task object to be used to track creation status
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param publication: Remote to create
    :type publication: Publication
    :return: Task
    """
    if not isinstance(publication, Publication):
        raise PulpV3InvalidArgumentError(
            "Expected type Publication got {0}".format(type(publication))
        )

    params = remove_invalid_creation_fields(publication)
    publication_type = None

    if isinstance(publication, FilePublication):
        publication_type = 'file'
    elif isinstance(publication, RpmPublication):
        publication_type = 'rpm'
    elif isinstance(publication, DebPublication):
        publication_type = 'deb'
    elif isinstance(publication, PythonPublication):
        publication_type = 'python'
    else:
        raise PulpV3InvalidArgumentError(
            "Client does not support given publication type. Supported types: {0}".format(
                ', '.join(PUBLICATION_TYPE_URL.keys())
            )
        )

    url = PUBLICATION_TYPE_URL[publication_type]
    result = client.post(url, params)
    return get_task(client, result['task'])


def new_publication_monitor(client: Pulp3Client, publication: Publication,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Creates a new instance of the given publication, and updates
    the publication object that was passed through
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param publication: Remote to create
    :type publication: Publication
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = new_publication(client, publication)
    task = monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    created_publication = get_publication(client, task.created_resources[0])
    publication.update(created_publication.dict())


def delete_publication(client: Pulp3Client, publication: Publication):
    """Deletes the requested publication and reutrns the task object
    for monitoring
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param publication: publication to delete
    :type publication: Publication
    :return: Task
    """
    if not isinstance(publication, Publication):
        raise PulpV3InvalidArgumentError(
            "Expected type Publication got {0}".format(type(publication))
        )

    result = client.delete(client, publication.pulp_href)
    return get_task(client, result['task'])


def delete_publication_monitor(client: Pulp3Client, publication: Publication,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Deletes the requested publication and monitors the task for completed. Returns the Task
    object on completion
    :param client: Client to connect to the API with
    :type client: Pulp3Client
    :param publication: Publication to delete
    :type publication: Publication
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = delete_publication(client, publication)
    task = monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    return task

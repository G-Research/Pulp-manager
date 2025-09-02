"""Methods for interacting with distributionsitories
"""

import re
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources.distribution import (
    Distribution, FileDistribution, RpmDistribution, DebDistribution, PythonDistribution,
	ContainerDistribution
)
from .tasks import get_task, monitor_task


DISTRIBUTION_INVALID_CREATION_FIELDS = [
    'pulp_href', 'pulp_created'
]
BASE_URL = '/distributions/'
DISTRIBUTION_TYPE_URL = {
    'file': '{0}file/file/'.format(BASE_URL),
    'rpm': '{0}rpm/rpm/'.format(BASE_URL),
    'deb': '{0}deb/apt/'.format(BASE_URL),
    'python': '{0}python/pypi/'.format(BASE_URL),
    'container': '{0}container/container/'.format(BASE_URL),
}


def remove_invalid_creation_fields(distribution: Distribution):
    """Removes the fields that aren't valid for the creation/updating
    of a Distribution object and returns a dict with the fields that can
    be used for the body
    :param distribution: Distribution to remove the fields from
    :type distribution: Distribution
    :return: dict
    """

    params = distribution.dict(exclude_unset=True)
    for field in DISTRIBUTION_INVALID_CREATION_FIELDS:
        if field in params:
            del params[field]

    # Either allowed repository or repository_version not both
    if (('repository' in params and params['repository'] is not None) and
            ('publication' in params and params['publication'] is not None)):
        raise PulpV3InvalidArgumentError(
            "Only repository or publication can be specified. Not both"
        )

    return params


def get_distribution_class(distribution_type: str):
    """Returns the class type of the distribution given the distribution type name
    :param distribution_type: Name of distribution type to get class for
    :type distribution_type: str
    :return: Distribution
    """

    distribution_class = None
    if distribution_type == 'file':
        distribution_class = FileDistribution
    elif distribution_type == 'rpm':
        distribution_class = RpmDistribution
    elif distribution_type == 'deb':
        distribution_class = DebDistribution
    elif distribution_type == 'python':
        distribution_class = PythonDistribution
    elif distribution_type == 'container':
        distribution_class = ContainerDistribution

    if distribution_class:
        return distribution_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given distribution type. Supported types: {0}".format(
            ', '.join(DISTRIBUTION_TYPE_URL.keys())
        )
    )


def get_all_distributions(client: Pulp3Client, distribution_type: str=None, params: dict=None):
    """Retrieves all distributions
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution_type: Limits the type of distribution to returbn e.g. rpm
    :type distribution_type: str
    :param params: dict of arguments to use to filter distributions to return
    :type params: dict
    :return: List of distributions
    """

    url = BASE_URL
    distribution_class = Distribution

    if distribution_type is not None and distribution_type in DISTRIBUTION_TYPE_URL:
        url = DISTRIBUTION_TYPE_URL[distribution_type]
        distribution_class = get_distribution_class(distribution_type)
    elif distribution_type is not None:
        raise PulpV3InvalidArgumentError(
            "Client does not support given distribution type {0}. Supported types: {1}".format(
                distribution_type, ', '.join(DISTRIBUTION_TYPE_URL.keys())
            )
        )

    distributions = client.get_page_results(url, params=params)
    return parse_obj_as(List[distribution_class], distributions)


def get_distribution(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified distribution from the given href

    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the distribution to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Distribution or None
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a distribution')

    match = re.match('/pulp/api/v3/distributions/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        distribution_type = match.groups()[0]
        distribution_class = get_distribution_class(distribution_type)
        result = client.get(href, params)
        return distribution_class(**result)


    raise PulpV3InvalidArgumentError(
        "href did not match pattern /pulp/api/v3/distributions/([a-z]+)/"
    )


def new_distribution(client: Pulp3Client, distribution: Distribution):
    """Creates a new instance of the given distribution, and returns
    a task object to use to monitor progress
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution: Distribution to create
    :type distribution: Distribution
    :return: Task
    """

    if not isinstance(distribution, Distribution):
        raise PulpV3InvalidArgumentError(
            "Expected type Distribution got {0}".format(type(distribution))
        )

    params = remove_invalid_creation_fields(distribution)
    distribution_type = None

    if isinstance(distribution, FileDistribution):
        distribution_type = 'file'
    elif isinstance(distribution, RpmDistribution):
        distribution_type = 'rpm'
    elif isinstance(distribution, DebDistribution):
        distribution_type = 'deb'
    elif isinstance(distribution, PythonDistribution):
        distribution_type = 'python'
    elif isinstance(distribution, ContainerDistribution):
        distribution_type = 'container'
    else:
        raise PulpV3InvalidArgumentError(
            "Client does not support given distribution type. Supported types: {0}".format(
                ', '.join(DISTRIBUTION_TYPE_URL.keys())
            )
        )

    url = DISTRIBUTION_TYPE_URL[distribution_type]
    result = client.post(url, params)
    return get_task(client, result['task'])


def new_distribution_monitor(client: Pulp3Client, distribution: Distribution,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Creates a new instance of the given distribution, and update the distribution
    object that was passed through
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution: Distribution to create
    :type distribution: Distribution
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    """

    task = new_distribution(client, distribution)
    task = monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    created_distribution = get_distribution(client, task.created_resources[0])
    distribution.update(created_distribution.dict())


def update_distribution(client: Pulp3Client, distribution: Distribution):
    """Updates an existing distribution and returns the task object
    for monitoring progress
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution: Distribution to update
    :type distribution: Distribution
    :return: Task
    """

    if not isinstance(distribution, Distribution):
        raise PulpV3InvalidArgumentError(
            "Expected type Distribution got {0}".format(type(distribution))
        )

    href = distribution.pulp_href
    params = remove_invalid_creation_fields(distribution)
    result = client.patch(href, params)
    return get_task(client, result['task'])


def update_distribution_monitor(client: Pulp3Client, distribution: Distribution,
        poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Updates an existing distribution and monitors the task for complete. Once completed
    updates the distirbution object that was passed through
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution: Distribution to update
    :type distribution: Distribution
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    """

    href = distribution.pulp_href
    task = update_distribution(client, distribution)
    monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)
    updated_distribution = get_distribution(client, href)
    distribution.update(updated_distribution.dict())


def delete_distribution(client: Pulp3Client, distribution: Distribution):
    """Deletes the request distribution and reutrns the task object
    for monitoring
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param distribution: distribution to delete
    :type distribution: Distribution
    :return: Task
    """

    if not isinstance(distribution, Distribution):
        raise PulpV3InvalidArgumentError(
            "Expected type Distribution got {0}".format(type(distribution))
        )

    result = client.delete(distribution.pulp_href)
    return get_task(client, result['task'])


def delete_distribution_monitor(client: Pulp3Client, distribution: Distribution,
         poll_interval_sec: int = 15, max_wait_count: int = 200, error: bool = True):
    """Deletes the requested distribution and monitors the task for completed. Returns the Task
    object on completion
    :param client: Client to connect to the API with
    :type client: Pulp3Client
    :param distribution: Distribution to delete
    :type distribution: Distribution
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    task = delete_distribution(client, distribution)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)

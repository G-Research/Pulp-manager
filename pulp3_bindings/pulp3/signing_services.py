"""Methods for interacting with remotesitories
"""

from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources import SigningService


BASE_URL = '/signing-services/'


def get_all_signing_services(client: Pulp3Client, params: dict=None):
    """Retrieves all signing services
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param params: dict of arguments to use to filter remotes to return
    :type params: dict
    :return: List of signing services
    """

    signing_services = client.get_page_results(BASE_URL, params=params)
    return parse_obj_as(List[SigningService], signing_services)


def get_signing_service(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified signing service from the given href
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the signing service to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Remote or None
    """

    if BASE_URL not in href:
        raise PulpV3InvalidArgumentError('href is not to a signing service')

    result = client.get(href, params)
    return SigningService(**result)

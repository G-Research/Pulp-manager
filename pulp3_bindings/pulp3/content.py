"""Methods for interacting with content, currently only supports interacting with content packages
"""

import re
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidArgumentError
from .resources.content import (
    Content, FilePackageContent, RpmPackageContent, DebPackageContent, PythonPackageContent
)


BASE_URL = '/content/'
# There are some content options supported
# on containers but currently only package content
# is supported
PACKAGE_CONTENT_TYPE_URL = {
    'file': '{0}file/files/'.format(BASE_URL),
    'rpm': '{0}rpm/packages/'.format(BASE_URL),
    'deb': '{0}deb/packages/'.format(BASE_URL),
    'python': '{0}python/packages/'.format(BASE_URL),
}


def get_content_package_class(content_package_type: str):
    """Returns the class type of the content pakcge given the content package type name
    :param content_package_type: Name of content package type to get class for
    :type content_package_type: str
    :return: PackageContent
    """

    content_package_class = None
    if content_package_type == 'file':
        content_package_class = FilePackageContent
    elif content_package_type == 'rpm':
        content_package_class = RpmPackageContent
    elif content_package_type == 'deb':
        content_package_class = DebPackageContent
    elif content_package_type == 'python':
        content_package_class = PythonPackageContent

    if content_package_class:
        return content_package_class

    raise PulpV3InvalidArgumentError(
        "Client does not support given content package type. Supported types: {0}".format(
            ', '.join(PACKAGE_CONTENT_TYPE_URL.keys())
        )
    )


def get_all_content(client: Pulp3Client, params: dict=None):
    """Retrieves all content units
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param params: dict of arguments to use to filter package content to return
    :type params: dict
    :return: List of package contents
    """

    content = client.get_page_results(BASE_URL, params=params)
    return parse_obj_as(List[Content], content)


def get_all_content_packages(client: Pulp3Client, package_type: str,  params: dict=None):
    """Retrieves all content packages
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param package_type: Limits the type of package content to return e.g. rpm
    :type package_type: str
    :param params: dict of arguments to use to filter package content to return
    :type params: dict
    :return: List of package contents
    """

    if package_type not in PACKAGE_CONTENT_TYPE_URL:
        raise PulpV3InvalidArgumentError(
            "Client does not support given package type {0}. Supported types: {1}".format(
                package_type, ', '.join(PACKAGE_CONTENT_TYPE_URL.keys())
            )
        )

    url = PACKAGE_CONTENT_TYPE_URL[package_type]
    content_package_class = get_content_package_class(package_type)
    packages = client.get_page_results(url, params=params)
    return parse_obj_as(List[content_package_class], packages)


def get_content_package(client: Pulp3Client, href: str, params: dict=None):
    """Gets the specified content package from the given href

    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param href: href of the content package to get
    :type href: str
    :param params: dict of arguments to use as query options
    :type params: dict
    :return: Remote or None
    """

    if BASE_URL not in href:
        PulpV3InvalidArgumentError('href is not to a content package')

    match = re.match('/pulp/api/v3/content/([a-z]+)/', href)
    if match and len(match.groups()) > 0:
        content_package_type = match.groups()[0]
        content_package_class = get_content_package_class(content_package_type)
        result = client.get(href, params)
        return content_package_class(**result)

    raise PulpV3InvalidArgumentError(
        "href did not match pattern /pulp/api/v3/content/([a-z]+)/"
    )

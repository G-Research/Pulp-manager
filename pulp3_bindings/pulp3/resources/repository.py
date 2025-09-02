"""implementation of the basic repository repo
"""

from datetime import datetime
from typing import Optional
from .base import Pulp3BaseModel


class Repository(Pulp3BaseModel):
    """Base repository that all repository types inherit from
    """

    pulp_href: Optional[str]
    pulp_created: Optional[datetime]
    versions_href: Optional[str]
    pulp_labels: Optional[dict]
    latest_version_href: Optional[str]
    name: str
    description: Optional[str]
    retain_repo_versions: Optional[int]
    remote: Optional[str]


class FileRepository(Repository):
    """File repository instance
    """

    autopublish: Optional[bool]
    manifest: Optional[str]


class RpmRepository(Repository):
    """RPM repository instance
    """

    autopublish: Optional[int]
    metadata_signing_service: Optional[str]
    metadata_checksum_type: Optional[str]
    package_checksum_type: Optional[str]
    gpgcheck: Optional[int]
    repo_gpgcheck: Optional[int]


class DebRepository(Repository):
    """DEB repository instance
    """

    signing_service: Optional[str]
    #pylint: disable=invalid-name
    signing_service_release_overrides: Optional[dict]


class PythonRepository(Repository):
    """Python repository instance
    """

    autopublish: Optional[int]

class ContainerRepository(Repository):
    """Container repository instnace
    """

    manifest_signing_service: Optional[str]


class RepositoryVersion(Pulp3BaseModel):
    """Base repository version that all the repository version types inherit from
    """

    pulp_href: str
    pulp_created: datetime
    number: int
    repository: str
    base_version: Optional[str]
    content_summary: dict


class FileRepositoryVersion(RepositoryVersion):
    """File Repository Version instance
    """


class RpmRepositoryVersion(RepositoryVersion):
    """RPM Repository Version instance
    """


class DebRepositoryVersion(RepositoryVersion):
    """DEB Repository Version instance
    """

class PythonRepositoryVersion(RepositoryVersion):
    """Python Repository Version instance
    """


class ContainerRepositoryVersion(RepositoryVersion):
    """Container Repository Version instance
    """

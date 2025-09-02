"""implementation of the basic repository repo
"""

from datetime import datetime
from typing import Optional
from .base import Pulp3BaseModel


class Publication(Pulp3BaseModel):
    """Base publication that all publication types inherit from
    """

    pulp_href: Optional[str]
    pulp_created: Optional[datetime]
    repository_version: Optional[str]
    repository: Optional[str]


class FilePublication(Publication):
    """File publication instance
    """

    manifest: Optional[str]


class RpmPublication(Publication):
    """RPM publication instance
    """

    metadata_checksum_type: str
    package_checksum_type: str
    gpgcheck: Optional[int]
    repo_gpgcheck: Optional[int]
    sqlite_metadata: Optional[bool]


class DebPublication(Publication):
    """DEB publication instnace
    """

    simple: Optional[bool]
    structured: Optional[bool]
    signing_service: Optional[str]


class PythonPublication(Publication):
    """Python publication instance
    """

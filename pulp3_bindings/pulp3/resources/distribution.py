"""Implementation of distributions
"""

from datetime import datetime
from typing import Optional
from .base import Pulp3BaseModel


class Distribution(Pulp3BaseModel):
    """Base distribution that all distribution types inherit from
    """

    pulp_href: Optional[str]
    pulp_created: Optional[datetime]
    base_path: str
    base_url: Optional[str]
    content_guard: Optional[str]
    hidden: Optional[bool]
    pulp_labels: Optional[dict]
    name: str
    repository: Optional[str]


class FileDistribution(Distribution):
    """Represents instance of a file distribution
    """

    publication: Optional[str]


class RpmDistribution(Distribution):
    """Represents instance of a rpm distribution
    """

    publication: Optional[str]


class DebDistribution(Distribution):
    """Represents instance of a deb distribution
    """

    publication: Optional[str]


class PythonDistribution(Distribution):
    """Represents instance of a python distribution
    """

    publication: Optional[str]
    allow_uploads: Optional[bool]
    remote: Optional[str]


class ContainerDistribution(Distribution):
    """Represents instance of a container distribution
    """

    repository_version: Optional[str]
    private: Optional[bool]
    description: Optional[str]

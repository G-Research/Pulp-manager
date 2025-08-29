"""Classes to represent remote repos
"""

from datetime import datetime
from typing import Optional, List
from .base import Pulp3BaseModel


class HiddenField(Pulp3BaseModel):
    """Hidden fields are fields set on repositories that contain secrets
    """

    name: str
    is_set: bool


class Remote(Pulp3BaseModel):
    """Base remote that all remote types inherit from
    """

    pulp_href: Optional[str]
    pulp_created: Optional[datetime]
    name: str
    url: str
    client_key: Optional[str]
    ca_cert: Optional[str]
    client_cert: Optional[str]
    tls_validation: Optional[bool]
    proxy_url: Optional[str]
    proxy_username: Optional[str]
    proxy_password: Optional[str]
    username: Optional[str]
    password: Optional[str]
    pulp_labels: Optional[dict]
    pulp_last_updated: Optional[datetime]
    download_concurrency: Optional[int]
    max_retries: Optional[int]
    policy: str
    total_timeout: Optional[int]
    connect_timeout: Optional[int]
    sock_connect_timeout: Optional[int]
    sock_read_timeout: Optional[int]
    headers: Optional[List[dict]]
    rate_limit: Optional[int]
    hidden_fields: Optional[List[HiddenField]]


class FileRemote(Remote):
    """Representation of an file remote
    """


class RpmRemote(Remote):
    """Representation of an RPM remote
    """


class DebRemote(Remote):
    """Representation of a DEB remote
    """

    distributions: str
    components: Optional[str]
    architectures: Optional[str]
    sync_sources: Optional[bool]
    sync_udebs: Optional[bool]
    sync_installer: Optional[bool]
    gpgkey: Optional[str]
    ignore_missing_package_indices: Optional[bool]

    @property
    def is_flat_repo(self):
        """Property that returns bool for whether a Deb remote is a flat repo.
        This is identified by the distributions field being set to "/"
        """

        return self.distributions == "/"


class PythonRemote(Remote):
    """Representation of a Python remote
    """

    includes: Optional[List[str]]
    excludes: Optional[List[str]]
    prereleases: Optional[bool]
    package_types: Optional[List[str]]
    keep_latest_packages: Optional[int]


class ContainerRemote(Remote):
    """Representation of a contianer remote
    """

    upstream_name: str
    include_tags: Optional[List[str]]
    exclude_tags: Optional[List[str]]
    sigstore: Optional[str]

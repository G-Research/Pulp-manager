"""implementation of content units
"""

from datetime import datetime
from typing import Optional, List
from .base import Pulp3BaseModel


class Content(Pulp3BaseModel):
    """Base content that all content types inherit from
    """

    pulp_href: Optional[str]
    pulp_created: Optional[datetime]
    artifacts: Optional[dict]


class FilePackageContent(Content):
    """File Package Content
    """

    artifact: Optional[str]
    relative_path: Optional[str]
    md5: Optional[str]
    sha1: Optional[str]
    sha224: Optional[str]
    sha256: Optional[str]
    sha384: Optional[str]
    sha512: Optional[str]


class RpmPackageContent(Content):
    """RPM Package Content representation
    """

    artifact: Optional[str]
    md5: Optional[str]
    sha1: Optional[str]
    sha224: Optional[str]
    sha256: Optional[str]
    sha384: Optional[str]
    sha512: Optional[str]
    artifact: Optional[str]
    name: Optional[str]
    epoch: Optional[str]
    version: Optional[str]
    release: Optional[str]
    arch: Optional[str]
    pkgId: Optional[str]
    checksum_type: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    url: Optional[str]
    changelogs: Optional[List]
    files: Optional[List]
    requires: Optional[List]
    provides: Optional[List]
    conflicts: Optional[List]
    obsoletes: Optional[List]
    suggests: Optional[List]
    enhances: Optional[List]
    recommends: Optional[List]
    suppliments: Optional[List]
    location: Optional[str]
    location_href: Optional[str]
    rpm_buildhost: Optional[str]
    rpm_group: Optional[str]
    rpm_license: Optional[str]
    rpm_packager: Optional[str]
    rpm_sourcerpm: Optional[str]
    rpm_vendor: Optional[str]
    rpm_header_start: Optional[int]
    rpm_header_end: Optional[int]
    is_modular: Optional[bool]
    size_archive: Optional[int]
    size_installed: Optional[int]
    size_package: Optional[int]
    time_build: Optional[int]
    time_file: Optional[int]


class DebPackageContent(Content):
    """DEB Package Content representation
    """

    artifact: Optional[str]
    md5: Optional[str]
    sha1: Optional[str]
    sha224: Optional[str]
    sha256: Optional[str]
    sha384: Optional[str]
    sha512: Optional[str]
    package: Optional[str]
    source: Optional[str]
    version: Optional[str]
    architecture: Optional[str]
    section: Optional[str]
    priority: Optional[str]
    origin: Optional[str]
    tag: Optional[str]
    bugs: Optional[str]
    essential: Optional[str]
    build_essential: Optional[str]
    installed_size: Optional[str]
    maintainer: Optional[str]
    original_maintainer: Optional[str]
    description: Optional[str]
    description_md5: Optional[str]
    homepage: Optional[str]
    built_using: Optional[str]
    auto_built_package: Optional[str]
    multi_arch: Optional[str]
    breaks: Optional[str]
    conflicts: Optional[str]
    depends: Optional[str]
    recommneds: Optional[str]
    suggests: Optional[str]
    enhances: Optional[str]
    pre_depends: Optional[str]
    provides: Optional[str]
    replaces: Optional[str]


class PythonPackageContent(Content):
    """Python pakcage content representation
    """

    artifact: Optional[str]
    filename: Optional[str]
    packagetype: Optional[str]
    name: Optional[str]
    version: Optional[str]
    sha256: Optional[str]
    metadata_version: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    description_content_type: Optional[str]
    keywords: Optional[str]
    home_page: Optional[str]
    download_url: Optional[str]
    author: Optional[str]
    author_email: Optional[str]
    maintainer: Optional[str]
    maintainer_email: Optional[str]
    license: Optional[str]
    requires_python: Optional[str]
    project_url: Optional[str]
    projects_urls: Optional[dict]
    platform: Optional[str]
    supported_platform: Optional[str]
    requires_dist: Optional[dict]
    provides_dist: Optional[dict]
    obsoletes_dist: Optional[dict]
    requires_external: Optional[dict]
    classifier: Optional[dict]

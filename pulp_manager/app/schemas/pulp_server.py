"""Pulp Server schema models
"""
# pylint: disable=no-name-in-module
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel


class PulpServer(BaseModel):
    """An instance of a pulp server to be managed
    """

    id: int
    name: str
    username: str
    vault_service_account_mount: Optional[str]
    repo_sync_health_rollup: Optional[str]
    repo_sync_health_rollup_date: Optional[datetime]
    snapshot_supported: Optional[bool]
    max_concurrent_snapshots: Optional[int]
    repo_config_registration_schedule: Optional[str]
    repo_config_registration_max_runtime: Optional[str]
    repo_config_registration_regex_include: Optional[str]
    repo_config_registration_regex_exclude: Optional[str]
    date_created: Optional[datetime]
    date_last_updated: Optional[datetime]

    class Config:
        """Internal class to state schema linked to ORM
        """

        orm_mode=True


class PulpServerRepo(BaseModel):
    """This is a repo that is on a specific pulp server
    """

    id: int
    name: str
    repo_type: str
    pulp_server_id: int
    repo_id: int
    repo_href: str
    remote_href: Optional[str]
    remote_feed: Optional[str]
    distribution_href: Optional[str]
    repo_sync_health: Optional[str]
    repo_sync_health_date: Optional[datetime]
    date_created: Optional[datetime]
    date_last_updated: Optional[datetime]

    class Config:
        """Internal class to state schema linked to ORM
        """

        orm_mode=True

class PulpServerRepoTask(BaseModel):
    """This a task associated with a repo"""

    pulp_server_repo_id: int
    pulp_server_repo: str
    task_id: int
    task: str

    class Config:
        """Internal class to state schema linked to ORM
        """
        orm_mode=True

class PulpServerSnapshotConfig(BaseModel):
    """Defines the repos that should be selected for snapshotting
    along with the snapshot prefix that should be used, which is prefixed
    infront of repos that are selected for snapshotting. When specifying
    max_runtime ensure that it is given in a format RQ can understand
    """

    max_runtime: str
    snapshot_prefix: str
    allow_snapshot_reuse: bool=False
    regex_include: Optional[str]
    regex_exclude: Optional[str]

class PulpServerRepoGroup(BaseModel):
    """Return model for repo groups associated with a pulp server"""

    pulp_server_id: int
    repo_group_id: int
    name: str
    schedule: Optional[str]
    max_concurrent_syncs: Optional[str]
    max_runtime: Optional[str]
    date_created: Optional[datetime]
    date_last_updated: Optional[datetime]

    class Config:
        """Internal class to state schema linked to ORM
        """
        orm_mode=True

class PulpServerSyncConfig(BaseModel):
    """Defines an adhoc sync that should be run against a pulp server.
    sync_options are repo type specific and need to be looked up via the pulp api
    to see which options can be sent to sync the specified group of repos
    """

    max_runtime: str
    max_concurrent_syncs: int
    regex_include: Optional[str]
    regex_exclude: Optional[str]
    source_pulp_server_name: Optional[str]
    sync_options: Optional[Dict]

class PulpServerRepoRemovalConfig(BaseModel):
    """Configuration for removing repositories from a Pulp server.
    This includes regex patterns for inclusion or exclusion, a maximum runtime
    for the removal task, and an option for a dry run to simulate the removal
    without actually deleting any repositories."""

    max_runtime: str
    regex_include: Optional[str] = None
    regex_exclude: Optional[str] = None
    dry_run: bool = True

class PulpServerFindRepoPackageContent(BaseModel):
    """Package content fields to search on within the repository version
    """

    name: Optional[str]
    version: Optional[str]
    sha256: Optional[str]


class PulpServerRemoveRepoContent(BaseModel):
    """Specifies the pulp content unit to remove from the requested repo along with how long the
    task should take to run.
    """

    content_href: str
    max_runtime: str
    force_publish: Optional[bool]

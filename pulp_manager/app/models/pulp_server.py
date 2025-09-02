"""Models for pulp servers
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    ForeignKey, Integer, String, UniqueConstraint, SmallInteger, Index, TEXT, DateTime, Boolean
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from pulp_manager.app.models.base import PulpManagerBase, PulpManagerBaseId
from pulp_manager.app.models.repo import RepoHealthStatus


class PulpServer(PulpManagerBaseId):
    """Pulp server that is managed by pulp_manager. Credentials for accessing the pulp server are
    read from vault

    :var name: fqdn of pulp instance to use to connect to the API
    :var repo_sync_health_rollup_id: ID representing the overall health of all repo syncs that
                                      have taken place
    :var repo_sync_health_rollup_date: date that the repo heath rollup was calculated
    :var username: Username of service account to use to connect to vault with
    :var vault_service_account_mount: Vault service account mount to use to read the
                                      credentials from
    :var snapshot_supported: Allow snapshots of repos to be taken on the pulp server
    :var max_concurrent_snapshots: Maximum number of repo snapshots that can run at once
    :var repo_config_registration_schedule: Specifies if repo configs held in git should be
                                            deployed to the pulp server and if so, specifies
                                            the schedule this should happen in cron syntax
    :var repo_config_registration_max_runtime: Max runtime the repo registration task sohuld run
                                               for 
    :var repo_config_registration_regex_include: Repos to include in repo regsitration
    :var repo_config_registration_regex_exclude: Repos to exclude form repo registration, if repos
                                                 are matched by regex include and regex exclude
                                                 then the exclude takes precedence
    """

    __tablename__ = "pulp_servers"

    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    repo_sync_health_rollup_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    repo_sync_health_rollup_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    username: Mapped[str] = mapped_column(String(25))
    vault_service_account_mount: Mapped[str] = mapped_column(String(56), nullable=True)
    snapshot_supported: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    max_concurrent_snapshots: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    repo_config_registration_schedule: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    repo_config_registration_max_runtime: Mapped[str] = mapped_column(String(10), nullable=True)
    repo_config_registration_regex_include: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    repo_config_registration_regex_exclude: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    repo_groups: Mapped[List["PulpServerRepoGroup"]] = relationship(
        back_populates="pulp_server",
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan",
        primaryjoin="PulpServer.id == PulpServerRepoGroup.pulp_server_id"

    )
    repos: Mapped[List["PulpServerRepo"]] = relationship(
        back_populates="pulp_server",
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan",
        lazy="raise"
    )
    pulp_slave_repo_groups: Mapped[List["PulpServerRepoGroup"]] = relationship(
        back_populates="pulp_master",
        passive_deletes=False,
        lazy="raise",
        primaryjoin="PulpServer.id == PulpServerRepoGroup.pulp_master_id"
    )

    __table_args__ = (
        UniqueConstraint("name", name="pulp_servers__unique__name"),
        Index("pulp_servers__index__repo_sync_health_rollup_id", repo_sync_health_rollup_id)
    )

    @property
    def repo_sync_health_rollup(self):
        """Getter for converting repo_sync_health_rollup_id into a string
        """

        if self.repo_sync_health_rollup_id is not None:
            return RepoHealthStatus(self.repo_sync_health_rollup_id).name
        return None

    @repo_sync_health_rollup.setter
    def repo_sync_health_rollup(self, value: str):
        """Takes a string and then sets repo_sync_health_rollup_id
        """

        self.repo_sync_health_rollup_id = RepoHealthStatus[value.lower()].value

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            id=self.id, name=self.name
        )


class PulpServerRepoGroup(PulpManagerBase):
    """Holds the config for a pulp server and its configure repo groups

    :var pulp_server_id: ID of the pulp server to link to the repo group
    :var repo_group_id: ID of the repo group to link to the pulp server
    :var schedule: if the sync of the repo is to be run on a schedule, than this hold the cron
                   syntax that is used for repeating the run of the run of the sync
    :var max_concurrent_syncs: Number of repo syncs that shoukd be run in parallel for the
                               repo group
    :var max_runtime: Specifies how long the job should be run for before it is cancelled and
                      considered failed. This uses the rq worker syntax for specifying
                      what the max runtime should be: https://python-rq.org/docs/jobs/
    """

    __tablename__ = "pulp_server_repo_groups"

    pulp_server_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "pulp_servers.id",
            name="pulp_server_repo_groups__fk__pulp_server_id",
            ondelete="CASCADE"
        ),
        primary_key=True,
        nullable=False
    )
    repo_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "repo_groups.id", name="pulp_server_repo_groups__fk__repo_group_id", ondelete="CASCADE"
        ),
        primary_key=True,
        nullable=False
    )
    schedule: Mapped[Optional[str]] = mapped_column(String(256))
    max_concurrent_syncs: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_runtime: Mapped[str] = mapped_column(String(10))
    pulp_master_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(
            "pulp_servers.id",
            name="pulp_server_repo_groups__fk__pulp_master_id",
        ),
        nullable=True
    )

    pulp_server: Mapped["PulpServer"] = relationship(
        back_populates="repo_groups",
        lazy="raise",
        foreign_keys=[pulp_server_id]
    )
    repo_group: Mapped["RepoGroup"] = relationship(
        back_populates="pulp_server_repo_groups", lazy="raise"
    )
    pulp_master: Mapped["PulpServer"] = relationship(
         back_populates="pulp_slave_repo_groups",
         lazy="raise",
         foreign_keys=[pulp_master_id]
    )

    @property
    def name(self):
        """Returns the name of the repo group from the repo_group relationship
        """

        return self.repo_group.name

    @property
    def regex_include(self):
        """Returns the regex_include expression from the repo_group relationship
        """

        return self.repo_group.regex_include

    @property
    def regex_exclude(self):
        """Retruns the regex_exclude expression from repo_group relationship
        """

        return self.repo_group.regex_exclude

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            pulp_server_id=self.pulp_server_id, repo_group_id=self.repo_group_id
        )


class PulpServerRepo(PulpManagerBaseId):
    """Holds the repo that exists in a pulp server. The creation and hosting of content in Pulp
    is made up 3-4 key object types:
    - remote: A remote contains configuration for synching a repo from an upstream source
    - repository: A repository holds the actual content for a repo, when a remote is synched,
                 remotes can be synched into more than one repository. When the content of a repo
                 is updated a new version of the repository is created called the repository 
                 version. To host this content a publication needs to be created for the repository
                 version which is then linked to a distribution which contains the path the repo
                 should be hosted at
    - publication: A Publication consists of the metadata of the content set and the artifacts of
                   each content unit in the content set
    - distribution: determines how and where a publication is served.
    For more information see: https://docs.pulpproject.org/pulpcore/concepts.html

    We assume there is a 1 to 1 mapping for a remote, to a repository
    to a distribution, and we can keep track of this information in
    this entity. For publications, pulp will host the latest published
    publication.

    :var pulp_server_id: ID of the pulp server the repo is associated with
    :var repo_id: ID of the the repo to associate with the pulp server
    :var repo_href: href of the repository on the pulp server
    :var remote_href: href of the remote associated with the repository
    :var remote_feed: The feed the remote is configured to sync from
    :var distribution_href: href of the distribution that is linked to the remote
    :var repo_sync_health_id: ID that represents the health of the repo
    :var repo_sync_health_date: datetime when the repo health was last calculated

    """

    __tablename__ = "pulp_server_repos"

    # Decided agqainst using a composite primary key as this table gets linked to a
    # pulp server repo sync task table, and felt it was easier to manage using a
    # dedicated for the records in this table
    pulp_server_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "pulp_servers.id", name="pulp_server_repos__fk__pulp_server_id", ondelete="CASCADE"
        ),
        nullable=False
    )
    repo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("repos.id", name="pulp_server_repos__fk__repo_id"),
        nullable=False
    )
    repo_href: Mapped[str] = mapped_column(TEXT, nullable=False)
    remote_href: Mapped[Optional[str]] = mapped_column(TEXT)
    remote_feed: Mapped[Optional[str]] = mapped_column(TEXT)
    distribution_href: Mapped[Optional[str]] = mapped_column(TEXT)
    repo_sync_health_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    repo_sync_health_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    pulp_server: Mapped["PulpServer"] = relationship(back_populates="repos")
    repo: Mapped["Repo"] = relationship(back_populates="pulp_server_repos")
    tasks: Mapped[List["PulpServerRepoTask"]] = relationship(
        back_populates="pulp_server_repo",
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan",
    )

    __table_args__ = (
        Index("pulp_server_repos__index__repo_sync_health_id", repo_sync_health_id),
        UniqueConstraint(
            "pulp_server_id", "repo_id", name="pulp_server_repos__unique__pulp_server_id__repo_id"
        )
    )

    @property
    def repo_sync_health(self):
        """Getter for converting repo_sync_health_id into human readable value
        """

        if self.repo_sync_health_id is not None:
            return RepoHealthStatus(self.repo_sync_health_id).name
        return None

    @repo_sync_health.setter
    def repo_sync_health(self, value):
        """Setter which takes string and sets repo_sync_health_id
        :param value: Name of task type to set
        :type value: str
        """

        self.repo_sync_health_id = RepoHealthStatus[value.lower()].value

    @property
    def name(self):
        """Gets the name of the repo from the repo relationship
        """

        return self.repo.name

    @property
    def repo_type(self):
        """Returns the repo type from the repo relationship
        """

        return self.repo.repo_type

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            id=self.id, pulp_server_id=self.pulp_server_id, repo_id=self.repo_id
        )


class PulpServerRepoTask(PulpManagerBase):
    """Links a pulp server repo to a task in which a series of action(s) were carried out
    """

    __tablename__ = "pulp_server_repo_tasks"

    pulp_server_repo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "pulp_server_repos.id",
            name="pulp_server_repo_tasks__fk__pulp_server_repo_id",
            ondelete="CASCADE"
        ),
        nullable=False,
        primary_key=True
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "tasks.id",
            name="pulp_server_repo_tasks__fk__task_id",
            ondelete="CASCADE"
        ),
        nullable=False,
        primary_key=True
    )

    pulp_server_repo: Mapped["PulpServerRepo"] = relationship(back_populates="tasks")
    task: Mapped["Task"] = relationship(back_populates="pulp_server_repo_tasks")

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(pulp_server_repo_id=self.pulp_server_repo_id, task_id=self.task_id)

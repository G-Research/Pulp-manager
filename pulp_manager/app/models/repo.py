"""Models for repos
"""

from enum import Enum
from typing import Optional, List
from sqlalchemy import UniqueConstraint, Index, String
from sqlalchemy.orm import mapped_column, Mapped, relationship
from pulp_manager.app.models.base import PulpManagerBaseId


class RepoHealthStatus(Enum):
    """Represents the health of repo

    Status explanations:
    - green: last three repo syncs have been successful
    - amber: last three repo syncs had an issue, or were skipped
    - red: more than the last three repo syncs had issues
    """

    #pylint: disable=invalid-name
    green = 1
    amber = 2
    red = 3


class Repo(PulpManagerBaseId):
    """Repo entity to hold ID, name and repo type. This is then mapped
    to a pulp server repo as hrefs won't be the same between different
    pulp instances

    :var name: Name of a repo
    :var repo_type: type of repo, e.g. rpm, deb
    """

    __tablename__ = "repos"

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    repo_type: Mapped[str] = mapped_column(String(20), nullable=False)

    pulp_server_repos: Mapped[List["PulpServerRepo"]] = relationship(back_populates="repo")

    __table_args__ = (
        UniqueConstraint("name", name="repos__unique__name"),
        Index("repos__index__rpm_type", "repo_type"),
        Index("repos__index__date_created", "date_created"),
        Index("repos__index__date_last_updated", "date_last_updated")
    )

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            id=self.id, name=self.name, repo_type=self.repo_type
        )


class RepoGroup(PulpManagerBaseId):
    """A repo group contains settings, that are used to decide what repo should be synched from a
    pulp server. Scheduling and run time infomation are held in the PulpServerRepoGroup entity

    :var name; Name of the repo group
    :var regex_include: regular expression to use for matching repos that should be included
                        in a sync
    :var regex_exclude: regular expression to use for matching repos that shold be omitted
                        from a sync
    """

    __tablename__ = "repo_groups"

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    regex_include: Mapped[Optional[str]] = mapped_column(String(512))
    regex_exclude: Mapped[Optional[str]] = mapped_column(String(512))

    pulp_server_repo_groups: Mapped[List["PulpServerRepoGroup"]] = relationship(
        back_populates="repo_group",
        cascade="save-update, merge, delete, delete-orphan",
        passive_deletes=True
    )

    __table_args__  = (
        UniqueConstraint("name", name="repo_groups__unique__name"),
    )

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            id=self.id, name=self.name, regex_include=self.regex_include,
            regex_exclude=self.regex_exclude
        )

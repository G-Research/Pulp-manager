"""repository for Repo
"""

from pulp_manager.app.models import Repo, RepoGroup
from pulp_manager.app.repositories.table_repository import TableRepository


class RepoRepository(TableRepository):
    """Repository for interacting with Repo entities
    """

    __model__ = Repo

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        raise NotImplementedError


class RepoGroupRepository(TableRepository):
    """Repository for interacting with repo group entities
    """

    __model__ = RepoGroup

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        raise NotImplementedError

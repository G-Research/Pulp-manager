"""repository for Pulp Server
"""
# pylint: disable=redefined-builtin
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.orm import aliased, joinedload, contains_eager
from pulp_manager.app.models import (
    PulpServer, PulpServerRepoGroup, PulpServerRepo, PulpServerRepoTask, Repo, RepoGroup, Task
)
from pulp_manager.app.repositories.table_repository import TableRepository


class PulpServerRepository(TableRepository):
    """Repository for interacting with PulpServer entities
    """

    __model__ = PulpServer
    __field_remap__ = {"repo_sync_health_rollup": PulpServer.repo_sync_health_rollup_id}

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        raise NotImplementedError

    def get_pulp_server_with_repos(self, **kwargs):
        """Returns a list of pulp server entities where joins have been carried out on the
        pulp_server_repos and repos tables to eagerly load relationships

        :param kwargs: arguments to filter server on
        :type kwargs: dict
        """

        filters = self._build_filter(False, **kwargs)
        query = select(self.__model__).options(joinedload(PulpServer.repos)\
                                        .options(joinedload(PulpServerRepo.repo)))\
                                        .where(and_(*filters))
        result = self.db.execute(query)
        return result.scalars().unique().all()

    def get_pulp_server_with_repo_groups(self, **kwargs):
        """Returns a list of pulp server entities where joins have been carried out
        on the pulp_server_repo_groups table and the repo_groups table, to eagerly load
        the relationships on nested tables

        :param kwargs: arguments to filter server on
        :type kwargs: dict
        :return: List[PulpServer]
        """

        filters = self._build_filter(False, **kwargs)
        query = select(self.__model__).options(joinedload(PulpServer.repo_groups)\
                                        .options(joinedload(PulpServerRepoGroup.repo_group))\
                                        .options(joinedload(PulpServerRepoGroup.pulp_master)))\
                                        .where(and_(*filters))
        result = self.db.execute(query)
        return result.scalars().unique().all()


class PulpServerRepoGroupRepository(TableRepository):
    """Repository for interacting with PulpServerRepoGroup
    """

    __model__ = PulpServerRepoGroup
    __remote_filter_name_to_field__ = {
        "name": RepoGroup.name
    }

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        # pulp_server and pulp_master relationships join back to same table.
        # To join back to two distinct pulp servers, need to create an alias
        # for each table which is then used in the join
        pulp_server_alias = aliased(PulpServer)
        pulp_master_alias = aliased(PulpServer)

        query = select(self.__model__).join(pulp_server_alias, self.__model__.pulp_server)\
                                      .join(self.__model__.repo_group)\
                                      .join(
                                          pulp_master_alias,
                                          self.__model__.pulp_master,
                                          isouter=True
                                      )

        if eager_load:
            query = query.options(contains_eager(self.__model__.pulp_server))\
                         .options(contains_eager(self.__model__.repo_group))\
                         .options(contains_eager(self.__model__.pulp_master))

        return query


    def get_by_id(self, id: int, eager: List=None):
        """PulpServerRepoGroup uses a composite key so getting by a single ID won't work
        """

        raise NotImplementedError(
            "PulpServerRepoGroup uses a composite primary key, get by a single ID not supported"
        )


class PulpServerRepoRepository(TableRepository):
    """Repository for interacting with PulpServerRepo
    """

    __model__ = PulpServerRepo
    __remote_filter_name_to_field__ = {
        "name": Repo.name,
        "pulp_server_name": PulpServer.name,
        "repo_type": Repo.repo_type
    }
    __field_remap__ = {
        "repo_sync_health": PulpServerRepo.repo_sync_health_id
    }

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        query = select(self.__model__).join(self.__model__.repo).join(self.__model__.pulp_server)

        if eager_load:
            query = query.options(contains_eager(self.__model__.repo))\
                         .options(contains_eager(self.__model__.pulp_server))

        return query


class PulpServerRepoTaskRepository(TableRepository):
    """Repository for interacting with PulpServerRepoTask
    """

    __model__ = PulpServerRepoTask
    __remote_filter_name_to_field__ = {
        "pulp_server_id": PulpServerRepo.pulp_server_id,
        "repo_id": PulpServerRepo.repo_id,
        "task_type": Task.task_type_id,
        "state": Task.state_id,
        "worker_name": Task.worker_name,
        "date_queued": Task.date_queued,
        "date_started": Task.date_started,
        "date_finished": Task.date_finished
    }

    def _get_base_filter_join_query(self, eager_load: bool):
        """Returns the query that contains all realted tables joined for querying

        :param eager_load: eagerly load all the joined table
        :type eager_load: bool
        """

        query = select(self.__model__).join(self.__model__.pulp_server_repo)\
                                      .join(PulpServerRepo.repo)\
                                      .join(self.__model__.task)

        if eager_load:
            query = query.options(contains_eager(self.__model__.pulp_server_repo)\
                                     .contains_eager(PulpServerRepo.repo))\
                         .options(contains_eager(self.__model__.task))

        return query

    def get_by_id(self, id: int, eager: List=None):
        """PulpServerRepoGroup uses a composite key so getting by a single ID won't work
        """

        raise NotImplementedError(
            "PulpServerRepoTask uses a composite primary key, get by a single ID not supported"
        )

    def update(self, entity, **kwargs):
        """Currently no reason for updates to be supported as this is a basic association table
        """

        raise NotImplementedError("PulpServerRepoTask updates are not supported")

    def bulk_update(self, entities: List):
        """Currently no reason for updates to be supported as this is a basic association table
        """

        raise NotImplementedError("PulpServerRepoTask updates are not supported")

    def delete(self, entity):
        """Delete should be handled with the removing of old expired tasks or the removal of a
        pulp server repo
        """

        raise NotImplementedError(
            "PulpServerRepoTask should be removed from deletion of a PulpServerRepo or Task"
        )

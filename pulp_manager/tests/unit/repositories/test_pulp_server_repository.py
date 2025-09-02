"""Tests for the pulp_server repository
"""
import json
import pytest
import sqlalchemy
from sqlalchemy.exc import InvalidRequestError

from pulp_manager.app.database import session, engine
from pulp_manager.app.models import (
    PulpServer, PulpServerRepoGroup, PulpServerRepo, PulpServerRepoTask
)
from pulp_manager.app.repositories import (
    PulpServerRepository, PulpServerRepoGroupRepository, PulpServerRepoRepository,
    PulpServerRepoTaskRepository, RepoGroupRepository, RepoRepository, TaskRepository
)


class TestPulpServerRepository:
    """Tests the pulp_server repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and pulp_server repository service for all services
        """

        self.db = session()
        self.pulp_server_repository = PulpServerRepository(self.db)

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()
        engine.dispose()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all pulp_server objects are returned.
        Sample data inserts at least two pulp_servers, so want to make sure more than one result is
        returned
        """

        result = self.pulp_server_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], PulpServer)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific pulp_server instance
        is returned
        """

        result = self.pulp_server_repository.filter(**{"name": "pulpserver1.domain.local"})
        assert len(result) == 1
        assert isinstance(result[0], PulpServer)

        result = self.pulp_server_repository.filter(**{
            "sort_by": "id",
            "order_by": "desc"
        })

        assert len(result) > 0
        assert result[0].id > result[1].id

    def test_lazy_eager_errors(self):
        """Tests lazy loading of properties which are marked as not being allowed to be lazy
        loaded result in errors
        """

        pulp_server =self.pulp_server_repository.first(**{"name": "pulpserver1.domain.local"})

        with pytest.raises(InvalidRequestError):
            pulp_server.repos

    def test_get_pulp_server_with_repos(self):
        """Tests that get_pulp_server_with_repos returns a pulp server with information loaded.
        If there are any problens an exception would be raised as lazy loading of the relationship
        is disabled
        """

        result = self.pulp_server_repository.get_pulp_server_with_repos(
            **{"name": "pulpserver1.domain.local"}
        )

        assert len(result) == 1
        pulp_server = result[0]
        assert len(pulp_server.repos) > 0
        # ensure no laxy load exceptions raised
        for pulp_server_repo in pulp_server.repos:
            name = pulp_server_repo.repo.name

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.pulp_server_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.pulp_server_repository.count_filter(**{"name": "pulpserver1.domain.local"})
        assert isinstance(result, int)
        assert result == 1

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.pulp_server_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_page_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.pulp_server_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_pulp_server_name = result["items"][0].name

        result = self.pulp_server_repository.filter_paged_result(page=2, page_size=1)
        page_1_pulp_server_name = result["items"][0].name

        assert page_0_pulp_server_name != page_1_pulp_server_name

    def test_get_first(self):
        """Tests that a single pulp_server is returned when a fitler is used
        """

        result = self.pulp_server_repository.first(**{"name": "pulpserver1.domain.local"})
        assert isinstance(result, PulpServer)

    def test_get_by_id(self):
        """Tests that requesting a pulp_server by ID returns the expected result
        """

        # First find a pulp_server based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.pulp_server_repository.filter(**{"name": "pulpserver1.domain.local"})
        pulp_server_id = result[0].id

        result = self.pulp_server_repository.get_by_id(pulp_server_id)
        assert isinstance(result, PulpServer)
        assert result.id == pulp_server_id

    def test_add(self):
        """Tests that a pulp_server instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        pulp_server = self.pulp_server_repository.add(**{
            "name": "test pulp_server_add.domain.local",
            "username": "username",
            "vault_service_account_mount": "service-accounts"
        })
        self.db.flush()

        assert isinstance(pulp_server, PulpServer)
        assert pulp_server.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of pulp_servers, returns the new objects
        db is flushed to generate pulp_server ids and then rolled back once assertions passed
        """

        pulp_servers = self.pulp_server_repository.bulk_add([
            {
                "name": "pulp_server_bulk1.domain.local",
                "username": "username",
                "vault_service_account_mount": "service-accounts"
            },
            {
                "name": "pulp_server_bulk2.domain.local",
                "username": "username",
                "vault_service_account_mount": "service-accounts"
            }
        ])
        self.db.flush()
        assert isinstance(pulp_servers, list)

        count = 0
        for pulp_server in pulp_servers:
            count += 1
            assert pulp_server.id is not None
            assert pulp_server.name == f"pulp_server_bulk{count}.domain.local"

    def test_update(self):
        """Tests updating a pulp_server is successful. This test works by adding a pulp_server
        flushing the db, updating the pulp_server, flushing the db again and then retrieving
        the updated pulp_server. Once assertions have passed the db is rolled back
        """

        pulp_server = self.pulp_server_repository.add(**{
            "name": "pulp_server.domain.local",
            "username": "username",
            "vault_service_account_mount": "service-accounts"
        })
        self.db.flush()

        pulp_server_id = pulp_server.id

        self.pulp_server_repository.update(pulp_server, **{"username": "username2"})
        self.db.flush()

        pulp_server = self.pulp_server_repository.get_by_id(pulp_server.id)
        assert pulp_server.username == "username2"
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of pulp_servers. Test works by creating two pulp_servers to update and flushing
        the db. The bulk update is called and then once assertions have passed the db is rolledback
        """

        pulp_servers_for_update = self.pulp_server_repository.bulk_add([
            {
                "name": "pulp_server_bulk1.domain.local",
                "username": "username",
                "vault_service_account_mount": "service-accounts"
            },
            {
                "name": "pulp_server_bulk2.domain.local",
                "username": "username",
                "vault_service_account_mount": "service-accounts"
            }
        ])
        self.db.flush()

        update_pulp_server_config = []
        for pulp_server in pulp_servers_for_update:
            update_pulp_server_config.append({
                "id": pulp_server.id,
                "username": "username2",
                "vault_service_account_mount": "service-accounts2"
            })

        self.pulp_server_repository.bulk_update(update_pulp_server_config)
        for p in pulp_servers_for_update:
            pulp_server = self.pulp_server_repository.get_by_id(p.id)
            assert pulp_server.username == "username2"
            assert pulp_server.vault_service_account_mount == "service-accounts2"

        self.db.rollback()

    def test_delete(self):
        """Tests removing a pulp_server from the db. A pulp_server is created and the db flushed.
        The pulp_server is then removed from the DB and once all assertions have passed the db
        is rolledback
        """

        pulp_server = self.pulp_server_repository.add(**{
            "name": "pulp_server_to_delete.domain.local",
            "username": "username2",
            "vault_service_account_mount": "service-accounts2"
        })
        self.db.flush()

        pulp_server_id = pulp_server.id

        self.pulp_server_repository.delete(pulp_server)
        self.db.flush()

        pulp_server = self.pulp_server_repository.get_by_id(pulp_server_id)
        assert pulp_server is None
        self.db.rollback()


class TestPulpServerRepoGroupRepository:
    """Tests the pulp server repo group repository. Carries out inserts updates and deletes to
    ensure that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and pulp server repo group repository service for all services
        """

        self.db = session()
        self.pulp_server_repository = PulpServerRepository(self.db)
        self.repo_group_repository = RepoGroupRepository(self.db)
        self.pulp_server_repo_group_repository = PulpServerRepoGroupRepository(self.db)

        # Get some test IDs that can be used for filter and add queries
        self.pulp_server_1_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver1.domain.local"}
        )).id
        self.pulp_server_2_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver2.domain.local"}
        )).id
        self.pulp_server_3_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver3.domain.local"}
        )).id
        self.repo_group_1_id = (self.repo_group_repository.first(**{
            "name": "repo group 1"
        })).id
        self.repo_group_2_id = (self.repo_group_repository.first(**{
            "name": "repo group 2"
        })).id

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all pulp server repo group objects
        are returned. Sample data inserts at least two pulp server repo groups, so want to make
        sure more than one result is returned
        """

        result = self.pulp_server_repo_group_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], PulpServerRepoGroup)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific pulp server repo group
        instance is returned
        """

        result = self.pulp_server_repo_group_repository.filter(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_group_id": self.repo_group_1_id
        })
        assert len(result) == 1
        assert isinstance(result[0], PulpServerRepoGroup)

    def test_filter_join(self):
        """Tests that filter join returns the expected results when query pulp server repo groups
        """

        result = self.pulp_server_repo_group_repository.filter_join(True, **{
            "name__match": "repo group"
        })

        assert len(result) == 4
        assert isinstance(result[0], PulpServerRepoGroup)

        for pulp_server_repo_group in result:
            assert "repo group" in pulp_server_repo_group.repo_group.name

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.pulp_server_repo_group_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.pulp_server_repo_group_repository.count_filter(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_group_id": self.repo_group_1_id
        })
        assert isinstance(result, int)
        assert result == 1

    def test_count_filter_join(self):
        """Tests that the correct count is returned for pulp server groups when a filter
        join is used
        """

        result = self.pulp_server_repo_group_repository.count_filter_join(**{
            "name__match": "repo group"
        })

        assert result == 4

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.pulp_server_repo_group_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_join_paged(self):
        """Tests the corrent number of repo groups are returned from a filter join paged result
        """

        result = self.pulp_server_repo_group_repository.filter_join_paged(
            True,
            page=1,
            page_size=1,
            **{"name__match": "repo group"}
        )

        assert len(result) == 1

    def test_filter_paged_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.pulp_server_repo_group_repository.filter_paged_result(
            page_size=1, eager=["pulp_server", "repo_group"]
        )
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        # Need to load relationship to get repo group name
        page_0_repo_group_name = result["items"][0].repo_group.name

        result = self.pulp_server_repo_group_repository.filter_paged_result(
            page=2, page_size=1, eager=["pulp_server", "repo_group"]
        )
        page_1_repo_group_name = result["items"][0].repo_group.name

        assert page_0_repo_group_name != page_1_repo_group_name

    def test_filter_join_paged_result(self):
        """Tests the correct number of results are returned from a filter join
        """

        result = self.pulp_server_repo_group_repository.filter_join_paged_result(
            True,
            page=1,
            page_size=1,
            **{"name__match": "repo group"}
        )

        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_repo_group_name = result["items"][0].repo_group.name

        result = self.pulp_server_repo_group_repository.filter_join_paged_result(
            True,
            page=2,
            page_size=1,
            **{"name__match": "repo group"}
        )
        page_1_repo_group_name = result["items"][0].repo_group.name

        assert page_0_repo_group_name != page_1_repo_group_name

    def test_get_first(self):
        """Tests that a single pulp server repo group is returned when a fitler is used
        """

        result = self.pulp_server_repo_group_repository.first(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_group_id": self.repo_group_1_id
        })
        assert isinstance(result, PulpServerRepoGroup)

    def test_get_by_id(self):
        """Tests that requesting a pulp server repo group by ID returns the expected result
        """

        with pytest.raises(NotImplementedError):
            self.pulp_server_repo_group_repository.get_by_id(1)

    def test_add(self):
        """Tests that a pulp server repo group instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        pulp_server_repo_group = self.pulp_server_repo_group_repository.add(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": self.repo_group_1_id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": 2,
            "max_runtime": "2h"
        })
        self.db.flush()

        # Need to eager laod the relationships for what carrying out the name checks
        # otherwise they get lazy loaded and you are given an error about attempted io
        # taking place, which won't work because using sync
        pulp_server_repo_group =  self.pulp_server_repo_group_repository.first(
            eager=["pulp_server", "repo_group"],
            **{"pulp_server_id": self.pulp_server_3_id, "repo_group_id": self.repo_group_1_id}
        )

        assert isinstance(pulp_server_repo_group, PulpServerRepoGroup)
        assert pulp_server_repo_group.pulp_server.name is not None
        assert pulp_server_repo_group.repo_group.name is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of pulp server repo groups, returns the new objects
        db is flushed to generate pulp_server ids and then rolled back once assertions passed
        """

        pulp_server_repo_groups = self.pulp_server_repo_group_repository.bulk_add([
            {
                "pulp_server_id": self.pulp_server_3_id,
                "repo_group_id": self.repo_group_1_id,
                "schedule": "0 0 * * *",
                "max_concurrent_syncs": 2,
                "max_runtime": "2h"
            },
            {
                "pulp_server_id": self.pulp_server_3_id,
                "repo_group_id": self.repo_group_2_id,
                "schedule": "0 0 * * *",
                "max_concurrent_syncs": 3,
                "max_runtime": "3h"
            }
        ])
        self.db.flush()
        assert isinstance(pulp_server_repo_groups, list)
        self.db.rollback()

    def test_update(self):
        """Tests updating a pulp server repo group is successful. This test works by adding a
        pulp server repo group  flushing the db, updating the pulp server repo group, flushing
        the db again and then retrieving the updated pulp server repo group. Once assertions have
        passed the db is rolled back
        """

        pulp_server_repo_group = self.pulp_server_repo_group_repository.add(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": self.repo_group_1_id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": 2,
            "max_runtime": "2h"
        })
        self.db.flush()

        self.pulp_server_repo_group_repository.update(
            pulp_server_repo_group, **{"max_concurrent_syncs": 4, "max_runtime": "4h"}
        )
        self.db.flush()

        pulp_server_repo_group = self.pulp_server_repo_group_repository.first(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": self.repo_group_1_id,
        })
        assert pulp_server_repo_group.max_concurrent_syncs == 4
        assert pulp_server_repo_group.max_runtime == "4h"
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of pulp server repo goups. Test works by creating two pulp server
        repo groups to update and flushing the db. The bulk update is called and then once
        assertions have passed the db is rolledback
        """

        pulp_server_repo_groups_for_update = self.pulp_server_repo_group_repository.bulk_add([
            {
                "pulp_server_id": self.pulp_server_3_id,
                "repo_group_id": self.repo_group_1_id,
                "schedule": "0 0 * * *",
                "max_concurrent_syncs": 2,
                "max_runtime": "2h"
            },
            {
                "pulp_server_id": self.pulp_server_3_id,
                "repo_group_id": self.repo_group_2_id,
                "schedule": "0 0 * * *",
                "max_concurrent_syncs": 3,
                "max_runtime": "4h"
            }
        ])
        self.db.flush()

        update_pulp_server_repo_group_config = []
        for repo_group in pulp_server_repo_groups_for_update:
            update_pulp_server_repo_group_config.append({
                "pulp_server_id": repo_group.pulp_server_id,
                "repo_group_id": repo_group.repo_group_id,
                "max_concurrent_syncs": 6,
                "max_runtime": "6h"
            })

        self.pulp_server_repo_group_repository.bulk_update(
            update_pulp_server_repo_group_config
        )
        for psrg in pulp_server_repo_groups_for_update:
            pulp_server_repo_group = self.pulp_server_repo_group_repository.first(**{
                "pulp_server_id": psrg.pulp_server_id,
                "repo_group_id": psrg.repo_group_id
            })
            assert pulp_server_repo_group.max_concurrent_syncs == 6
            assert pulp_server_repo_group.max_runtime == "6h"

        self.db.rollback()

    def test_delete(self):
        """Tests removing a pulp server repo group from the db. A pulp server repo group is created
        and the db flushed. The pulp server repo group is then removed from the DB and once all
        assertions have passed the db is rolled back
        """

        pulp_server_repo_group = self.pulp_server_repo_group_repository.add(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": self.repo_group_2_id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": 3,
            "max_runtime": "4h"
        })
        self.db.flush()

        self.pulp_server_repo_group_repository.delete(pulp_server_repo_group)
        self.db.flush()

        pulp_server_repo_group = self.pulp_server_repo_group_repository.first(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": self.repo_group_2_id
        })
        assert pulp_server_repo_group is None
        self.db.rollback()

    def test_pulp_server_delete(self):
        """Tests that when a pulp server is removed associated pulp server repo groups are
        also removed
        """

        pulp_server_to_remove = self.pulp_server_repository.add(**{
            "name": "pulp_remove.domain.local",
            "username": "username",
            "vault_service_account_mount": "service-accounts"
        })

        self.db.flush()

        pulp_server_repo_group_count_before = self.pulp_server_repo_group_repository.count()

        pulp_server_repo_group = self.pulp_server_repo_group_repository.add(**{
            "pulp_server_id": pulp_server_to_remove.id,
            "repo_group_id": self.repo_group_2_id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": 3,
            "max_runtime": "4h"
        })
        self.db.flush()

        pulp_server_repo_group_count_after_add = self.pulp_server_repo_group_repository.count()
        assert pulp_server_repo_group_count_after_add == pulp_server_repo_group_count_before + 1

        self.pulp_server_repository.delete(pulp_server_to_remove)
        self.db.flush()

        pulp_server_repo_group_count_after_remove = self.pulp_server_repo_group_repository.count()
        assert pulp_server_repo_group_count_before == pulp_server_repo_group_count_after_remove

    def test_repo_group_delete(self):
        """Tests that when a repo group is removed the associated pulp server repo groups are
        also removed
        """

        repo_group_to_remove = self.repo_group_repository.add(**{
            "name": "repo_group_to_remove"
        })
        self.db.flush()

        pulp_server_repo_group_count_before = self.pulp_server_repo_group_repository.count()
        pulp_server_repo_group = self.pulp_server_repo_group_repository.add(**{
            "pulp_server_id": self.pulp_server_3_id,
            "repo_group_id": repo_group_to_remove.id,
            "schedule": "0 0 * * *",
            "max_concurrent_syncs": 3,
            "max_runtime": "4h"
        })
        self.db.flush()

        pulp_server_repo_group_count_after_add = self.pulp_server_repo_group_repository.count()
        assert pulp_server_repo_group_count_after_add == pulp_server_repo_group_count_before + 1

        self.repo_group_repository.delete(repo_group_to_remove)
        self.db.flush()

        pulp_server_repo_group_count_after_remove = self.pulp_server_repo_group_repository.count()
        assert pulp_server_repo_group_count_before == pulp_server_repo_group_count_after_remove


class TestPulpServerRepoRepository:
    """Tests the pulp server repo repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and pulp server repo repository service for all services
        """

        self.db = session()
        self.pulp_server_repo_repository = PulpServerRepoRepository(self.db)
        self.pulp_server_repository = PulpServerRepository(self.db)
        self.repo_repository = RepoRepository(self.db)

        # IDs to use for setting up some test repos
        self.pulp_server_1_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver1.domain.local"}
        )).id
        self.pulp_server_2_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver2.domain.local"}
        )).id
        self.repo_1_id = (self.repo_repository.first(**{
            "name": "repo1"
        })).id
        self.repo_2_id = (self.repo_repository.first(**{
            "name": "repo2"
        })).id

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all pulp server repo objects are
        returned. Sample data inserts at least two pulp server reoi groups, so want to make sure
        more than one result is returned
        """

        result = self.pulp_server_repo_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], PulpServerRepo)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific pulp server repo
        is returned
        """

        result = self.pulp_server_repo_repository.filter(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_id": self.repo_1_id
        })
        assert len(result) == 1
        assert isinstance(result[0], PulpServerRepo)

    def test_filter_join(self):
        """Tests filter join returns the expected results when query for a particular repo type
        """

        result = self.pulp_server_repo_repository.filter_join(True, **{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_type": "rpm"
        })

        assert len(result) == 1
        assert isinstance(result[0], PulpServerRepo)
        assert result[0].repo.repo_type == "rpm"

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.pulp_server_repo_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.pulp_server_repo_repository.count_filter(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_id": self.repo_1_id
        })
        assert isinstance(result, int)
        assert result == 1

    def test_count_filter_join(self):
        """Tests that the correct number is returned by count filter join function
        """

        result = self.pulp_server_repo_repository.count_filter_join(**{
            "pulp_server_id": self.pulp_server_1_id,
            "name__match": "repo"
        })

        assert isinstance(result, int)
        assert result == 2

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.pulp_server_repo_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_join_paged(self):
        """Checks correct number of results are returned from a paged filter join
        """

        result = self.pulp_server_repo_repository.filter_join_paged(
            False,
            page=1,
            page_size=1,
            **{
                "pulp_server_id": self.pulp_server_1_id,
                "name__match": "repo"
            }
        )

        assert len(result) == 1

    def test_filter_paged_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.pulp_server_repo_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_pulp_repo_id = result["items"][0].repo_id

        result = self.pulp_server_repo_repository.filter_paged_result(page=2, page_size=1)
        page_1_pulp_repo_id = result["items"][0].repo_id

        assert page_0_pulp_repo_id != page_1_pulp_repo_id

    def test_filter_join_paged_result(self):
        """Tests the the combined page count and results object is returned as expected
        """

        result = self.pulp_server_repo_repository.filter_join_paged_result(
            False,
            page=1,
            page_size=1,
            **{
                "pulp_server_id": self.pulp_server_1_id,
                "name__match": "repo"
            }
        )

        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] == 2

        page_0_pulp_repo_id = result["items"][0].repo_id

        result = self.pulp_server_repo_repository.filter_join_paged_result(
            False,
            page=2,
            page_size=1,
            **{
                "pulp_server_id": self.pulp_server_1_id,
                "name__match": "repo"
            }
        )
        page_1_pulp_repo_id = result["items"][0].repo_id

        assert page_0_pulp_repo_id != page_1_pulp_repo_id

    def test_get_first(self):
        """Tests that a single pulp_server is returned when a fitler is used
        """

        result = self.pulp_server_repo_repository.first(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_id": self.repo_1_id
        })
        assert isinstance(result, PulpServerRepo)

    def test_get_by_id(self):
        """Tests that requesting a pulp_server by ID returns the expected result
        """

        # First find a pulp_server based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.pulp_server_repo_repository.filter(**{
            "pulp_server_id": self.pulp_server_1_id,
            "repo_id": self.repo_1_id
        })
        pulp_server_repo_id = result[0].id

        result = self.pulp_server_repo_repository.get_by_id(pulp_server_repo_id)
        assert isinstance(result, PulpServerRepo)
        assert result.id == pulp_server_repo_id

    def test_add(self):
        """Tests that a pulp server repo instance is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        pulp_server_repo = self.pulp_server_repo_repository.add(**{
            "pulp_server_id": self.pulp_server_2_id,
            "repo_id": self.repo_1_id,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
        })
        self.db.flush()

        assert isinstance(pulp_server_repo, PulpServerRepo)
        assert pulp_server_repo.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of pulp_servers, returns the new objects
        db is flushed to generate pulp_server ids and then rolled back once assertions passed
        """

        pulp_server_repos = self.pulp_server_repo_repository.bulk_add([
            {
                "pulp_server_id": self.pulp_server_2_id,
                "repo_id": self.repo_1_id,
                "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
            },
            {
                "pulp_server_id": self.pulp_server_2_id,
                "repo_id": self.repo_2_id,
                "repo_href": "/pulp/api/v3/repositories/deb/apt/def"
            }
        ])
        self.db.flush()
        assert isinstance(pulp_server_repos, list)
        assert isinstance(pulp_server_repos[0], PulpServerRepo)
        assert pulp_server_repos[0].pulp_server_id == self.pulp_server_2_id


    def test_update(self):
        """Tests updating a pulp server repo is successful. This test works by adding a pulp server
        repo flushing the db, updating the pulp server repo, flushing the db again and then retrieving
        the updated pulp server repo. Once assertions have passed the db is rolled back
        """

        pulp_server_repo = self.pulp_server_repo_repository.add(**{
            "pulp_server_id": self.pulp_server_2_id,
            "repo_id": self.repo_1_id,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
        })
        self.db.flush()

        pulp_server_repo_id = pulp_server_repo.id

        self.pulp_server_repo_repository.update(
            pulp_server_repo, **{"remote_href": "/pulp/api/v3/remotes/rpm/rpm/abc"}
        )
        self.db.flush()

        pulp_server_repo = self.pulp_server_repo_repository.get_by_id(pulp_server_repo.id)
        assert pulp_server_repo.remote_href == "/pulp/api/v3/remotes/rpm/rpm/abc"
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of pulp server repos. Test works by creating two pulp server repos
        to update and flushing the db. The bulk update is called and then once assertions have
        passed the db is rolledback
        """

        pulp_server_repos_for_update = self.pulp_server_repo_repository.bulk_add([
            {
                "pulp_server_id": self.pulp_server_2_id,
                "repo_id": self.repo_1_id,
                "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
            },
            {
                "pulp_server_id": self.pulp_server_2_id,
                "repo_id": self.repo_2_id,
                "repo_href": "/pulp/api/v3/repositories/deb/apt/def"
            }
        ])
        self.db.flush()

        update_pulp_server_repo_config = []
        for pulp_server_repo in pulp_server_repos_for_update:
            update_pulp_server_repo_config.append({
                "id": pulp_server_repo.id,
                "remote_href": "updated-remote",
                "distribution_href": "updated-distribution"
            })

        self.pulp_server_repo_repository.bulk_update(update_pulp_server_repo_config)
        for psr in pulp_server_repos_for_update:
            pulp_server_repo = self.pulp_server_repo_repository.get_by_id(psr.id)
            assert pulp_server_repo.remote_href == "updated-remote"
            assert pulp_server_repo.distribution_href == "updated-distribution"

        self.db.rollback()

    def test_delete(self):
        """Tests removing a pulp server repo from the db. A pulp server repo is created and the db
        flushed. The pulp server repo is then removed from the DB and once all assertions have
        passed the db is rolledback
        """

        pulp_server_repo = self.pulp_server_repo_repository.add(**{
            "pulp_server_id": self.pulp_server_2_id,
            "repo_id": self.repo_1_id,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
        })
        self.db.flush()

        pulp_server_repo_id = pulp_server_repo.id

        self.pulp_server_repo_repository.delete(pulp_server_repo)
        self.db.flush()

        pulp_server_repo = self.pulp_server_repo_repository.get_by_id(pulp_server_repo_id)
        assert pulp_server_repo is None
        self.db.rollback()

    def test_pulp_server_delete(self):
        """Tests that when a pulp server is removed the associated pulp server repos are removed
        """

        pulp_server_to_remove = self.pulp_server_repository.add(**{
            "name": "pulp_server_to_remove",
            "username": "username",
            "vault_service_account_mount": "service-accounts"
        })
        self.db.flush()

        count_before_pulp_repo_add = self.pulp_server_repo_repository.count()

        pulp_server_repo = self.pulp_server_repo_repository.add(**{
            "pulp_server_id": pulp_server_to_remove.id,
            "repo_id": self.repo_1_id,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/abc"
        })
        self.db.flush()

        count_after_pulp_repo_add = self.pulp_server_repo_repository.count()
        assert count_after_pulp_repo_add == count_before_pulp_repo_add + 1

        self.pulp_server_repository.delete(pulp_server_to_remove)
        self.db.flush()

        count_after_pulp_server_delete = self.pulp_server_repo_repository.count()
        assert count_before_pulp_repo_add == count_after_pulp_server_delete
        self.db.rollback()

    def test_repo_delete_fail(self):
        """When a Repo entity is to be removed from the database this should fail when
        there is an association with an existing pulp server
        """

        # repo1 from smaple is linked to an existing pulp server so if we try and remove it
        # foreign key constraint on the PulpServerRepo should result in a failure
        repo = self.repo_repository.get_by_id(self.repo_1_id)
        pulp_server_repo_count = self.pulp_server_repo_repository.count_filter(
            **{"repo_id": self.repo_1_id}
        )
        assert pulp_server_repo_count > 0
        self.repo_repository.delete(repo)

        with pytest.raises(sqlalchemy.exc.IntegrityError):
            self.db.flush()


class TestPulpServerRepoTaskRepository:
    """Tests the pulp server repo task repository. Carries out inserts updates and deletes
    to ensure that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db andrepositories service for all services
        """

        self.db = session()
        self.pulp_server_repository = PulpServerRepository(self.db)
        self.pulp_server_repo_repository = PulpServerRepoRepository(self.db)
        self.pulp_server_repo_task_repository = PulpServerRepoTaskRepository(self.db)
        self.task_repository = TaskRepository(self.db)

        self.pulp_server_1_id = (self.pulp_server_repository.first(**{
            "name": "pulpserver1.domain.local"})
        ).id
        sample_pulp_server_repos = self.pulp_server_repo_repository.filter()
        self.pulp_server_repo_1_id = sample_pulp_server_repos[0].id
        self.pulp_server_repo_2_id = sample_pulp_server_repos[1].id
        self.task_1_id = (self.task_repository.first(**{"name": "dummy task 1"})).id
        self.task_2_id = (self.task_repository.first(**{"name": "dummy task 2"})).id
        self.task_3_id = (self.task_repository.first(**{"name": "dummy task 3"})).id

    def teardown_method(self):
        """Close db connection
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all pulp server repo task objects are
        returned. Sample data inserts at least two pulp_servers, so want to make sure more than one
        result is returned
        """

        result = self.pulp_server_repo_task_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], PulpServerRepoTask)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific pulp server tasks are returned
        is returned
        """

        result = self.pulp_server_repo_task_repository.filter(**{"task_id": self.task_1_id})
        assert len(result) == 1
        assert isinstance(result[0], PulpServerRepoTask)

    def test_filter_join(self):
        """Tests filter join returns the expected results where querying for tasks in a particular
        state
        """

        result = self.pulp_server_repo_task_repository.filter_join(True, **{
            "state": "queued",
            "task_type": "repo_sync"
        })
        assert len(result) == 2
        for task in result:
            assert task.task.state == "queued"
            assert task.task.task_type == "repo_sync"

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.pulp_server_repo_task_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.pulp_server_repo_task_repository.count_filter(**{
            "task_id": self.task_1_id
        })
        assert isinstance(result, int)
        assert result == 1

    def test_count_filter_join(self):
        """Tests that the corect number is returned by the count filter join
        """

        result = self.pulp_server_repo_task_repository.count_filter_join(**{
            "state": "queued",
            "task_type": "repo_sync"
        })
        assert result == 2

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.pulp_server_repo_task_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_join_paged(self):
        """Tests that only the number ofrequested results are returned
        """

        result = self.pulp_server_repo_task_repository.filter_join_paged(
            True,
            page=1,
            page_size=1,
            **{
                "state": "queued",
                "task_type": "repo_sync"
            }
        )
        assert len(result) == 1

    def test_filter_paged_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.pulp_server_repo_task_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_task_id = result["items"][0].task_id

        result = self.pulp_server_repo_task_repository.filter_paged_result(
            page=2, page_size=1
        )
        page_1_task_id = result["items"][0].task_id

        assert page_0_task_id != page_1_task_id

    def test_filter_join_paged_result(self):
        """Tests that the combined page count and results object is returned as expected
        """

        result = self.pulp_server_repo_task_repository.filter_join_paged_result(
            True,
            page=1,
            page_size=1,
            **{
                "state": "queued",
                "task_type": "repo_sync"
            }
        )

        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] == 2

        page_0_pulp_server_repo_id = result["items"][0].pulp_server_repo_id

        result = self.pulp_server_repo_task_repository.filter_join_paged_result(
            True,
            page=2,
            page_size=1,
            **{
                "state": "queued",
                "task_type": "repo_sync"
            }
        )
        
        page_1_pulp_server_repo_id = result["items"][0].pulp_server_repo_id

        assert page_0_pulp_server_repo_id != page_1_pulp_server_repo_id

    def test_get_first(self):
        """Tests that a single pulp_server is returned when a fitler is used
        """

        result = self.pulp_server_repo_task_repository.first(**{
            "task_id": self.task_1_id
        })
        assert isinstance(result, PulpServerRepoTask)

    def test_get_by_id(self):
        """Tests exception is raised as pulp_server_repo_tasks table contains a composite
        primary key
        """

        with pytest.raises(NotImplementedError):
            self.pulp_server_repo_task_repository.get_by_id(1)

    def test_add(self):
        """Tests that a pulp server repo task instance is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        pulp_server_repo_task = self.pulp_server_repo_task_repository.add(**{
            "pulp_server_repo_id": self.pulp_server_repo_2_id,
            "task_id": self.task_3_id
        })
        self.db.flush()

        assert isinstance(pulp_server_repo_task, PulpServerRepoTask)
        self.db.rollback()

    def test_update(self):
        """Test NotImplementedError is raised
        """

        with pytest.raises(NotImplementedError):
            self.pulp_server_repo_task_repository.update(None, **{})

    def test_bulk_update(self):
        """Test NotImplementedError is raised
        """

        with pytest.raises(NotImplementedError):
            self.pulp_server_repo_task_repository.bulk_update([])

    def test_delete(self):
        """Test NotImplementedError is raised
        """

        with pytest.raises(NotImplementedError):
            self.pulp_server_repo_task_repository.delete(None)

    def test_delete_task(self):
        """Tests that when a task is deleted the associated PulpServerRepoTask is removed
        """

        pulp_server_repo_task_count_before_delete = self.pulp_server_repo_task_repository.count()

        task1 = self.task_repository.get_by_id(self.task_1_id)
        self.task_repository.delete(task1)
        self.db.flush()

        pulp_server_repo_task_count_after_delete = self.pulp_server_repo_task_repository.count()
        assert pulp_server_repo_task_count_after_delete < pulp_server_repo_task_count_before_delete
        self.db.rollback()

    def test_delete_pulp_server_repo(self):
        """Tests that when a pul pserver repo is deleted the asosciated PulpServerRepoTask
        is removed
        """
        
        pulp_server_repo_task_count_before_delete = self.pulp_server_repo_task_repository.count()

        pulp_server_repo = self.pulp_server_repo_repository.get_by_id(self.pulp_server_repo_1_id)
        self.pulp_server_repo_repository.delete(pulp_server_repo)
        self.db.flush()

        pulp_server_repo_task_count_after_delete = self.pulp_server_repo_task_repository.count()
        assert pulp_server_repo_task_count_after_delete < pulp_server_repo_task_count_before_delete
        self.db.rollback()

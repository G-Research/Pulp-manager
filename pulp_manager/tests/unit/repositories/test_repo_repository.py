"""Tests for the repo repository
"""
import json
import pytest

from pulp_manager.app.database import session, engine
from pulp_manager.app.models import Repo, RepoGroup
from pulp_manager.app.repositories import RepoRepository, RepoGroupRepository


class TestRepoRepository:
    """Tests the repo repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and repo repository service for all services
        """

        self.db = session()
        self.repo_repository = RepoRepository(self.db)

    def teardown_method(self):
        """Ensure db connections closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all repo objects are returned.
        Sample data inserts at least two repos, so want to make sure more than one result is
        returned
        """

        result = self.repo_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], Repo)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific repo instance
        is returned
        """

        result = self.repo_repository.filter(**{"repo_type": "rpm"})
        assert len(result) == 1
        assert isinstance(result[0], Repo)

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.repo_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.repo_repository.count_filter(**{"name": "repo2"})
        assert isinstance(result, int)
        assert result == 1

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.repo_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_page_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.repo_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_repo_name = result["items"][0].name

        result = self.repo_repository.filter_paged_result(page=2, page_size=1)
        page_1_repo_name = result["items"][0].name

        assert page_0_repo_name != page_1_repo_name

    def test_get_first(self):
        """Tests that a single repo is returned when a fitler is used
        """

        result = self.repo_repository.first(**{"name": "repo1"})
        assert isinstance(result, Repo)

    def test_get_by_id(self):
        """Tests that requesting a repo by ID returns the expected result
        """

        # First find a repo based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.repo_repository.filter(**{"name": "repo1"})
        repo_id = result[0].id

        result = self.repo_repository.get_by_id(repo_id)
        assert isinstance(result, Repo)
        assert result.id == repo_id

    def test_add(self):
        """Tests that a repo instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        repo = self.repo_repository.add(**{
            "name": "test repo",
            "repo_type": "rpm"
        })
        self.db.flush()

        assert isinstance(repo, Repo)
        assert repo.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of repos, returns the new objects
        db is flushed to generate repo ids and then rolled back once assertions passed
        """

        repos = self.repo_repository.bulk_add([
            {
                "name": "test repo 1",
                "repo_type": "rpm"
            },
            {
                "name": "test repo 2",
                "repo_type": "deb"
            },
            {
                "name": "test repo 3",
                "repo_type": "rpm"
            },
        ])
        self.db.flush()
        assert isinstance(repos, list)

        count = 0
        for repo in repos:
            count += 1
            assert repo.id is not None
            assert repo.name == f"test repo {count}"

    def test_update(self):
        """Tests updating a repo is successful. This test works by adding a repo
        flushing the db, updating the repo, flushing the db again and then retrieving
        the updated repo. Once assertions have passed the db is rolled back
        """

        repo = self.repo_repository.add(**{
            "name": "repo to update",
            "repo_type": "rpm"
        })
        self.db.flush()

        repo_id = repo.id

        self.repo_repository.update(repo, **{"repo_type": "deb"})
        self.db.flush()

        repo = self.repo_repository.get_by_id(repo.id)
        assert repo.repo_type == "deb"
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of repos. Test works by creating two repos to update and flushing
        the db. The bulk update is called and then once assertions have passed the db is rolledback
        """

        repos_for_update = self.repo_repository.bulk_add([
            {
                "name": "repo to update 1",
                "repo_type": "rpm"
            },
            {
                "name": "repo to update 2",
                "repo_type": "rpm"
            }
        ])
        self.db.flush()

        update_repo_config = []
        for repo in repos_for_update:
            update_repo_config.append({"id": repo.id, "repo_type": "deb"})

        self.repo_repository.bulk_update(update_repo_config)
        for r in repos_for_update:
            repo = self.repo_repository.get_by_id(r.id)
            assert repo.repo_type == "deb"

        self.db.rollback()

    def test_delete(self):
        """Tests removing a repo from the db. A repo is created and the db flushed.
        The repo is then removed from the DB and once all assertions have passed the db
        is rolledback
        """

        repo = self.repo_repository.add(**{
            "name": "repo to delete",
            "repo_type": "rpm"
        })
        self.db.flush()

        repo_id = repo.id

        self.repo_repository.delete(repo)
        self.db.flush()

        repo = self.repo_repository.get_by_id(repo_id)
        assert repo is None
        self.db.rollback()


class TestRepoGroupRepository:
    """Tests the repo group repository. Carries out inserts updates and deletes to ensure
    that foreign key constraints and cascading deletes work as expected
    """

    def setup_method(self):
        """Setup the db and repo repository service for all services
        """

        self.db = session()
        self.repo_group_repository = RepoGroupRepository(self.db)

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()

    def test_no_filter(self):
        """Tests that when no filtering is applied to the db all repo group objects are returned.
        Sample data inserts at least two repo groups, so want to make sure more than one result is
        returned
        """

        result = self.repo_group_repository.filter()
        assert len(result) > 1
        assert isinstance(result[0], RepoGroup)

    def test_filter(self):
        """Tests that when filtering is applied to the query the specific repo group instance
        is returned
        """

        result = self.repo_group_repository.filter(**{"name": "repo group 1"})
        assert len(result) == 1
        assert isinstance(result[0], RepoGroup)

    def test_count(self):
        """Tests that an int is returned by the count function
        """

        result = self.repo_group_repository.count()
        assert isinstance(result, int)
        assert result > 0

    def test_count_filter(self):
        """Tests that an int is returned by the count filter function
        """

        result = self.repo_group_repository.count_filter(**{"name": "repo group 2"})
        assert isinstance(result, int)
        assert result == 1

    def test_filter_paged(self):
        """Tests that only the number of requested results is returned
        """

        result = self.repo_group_repository.filter_paged(page_size=1)
        assert len(result) == 1

    def test_filter_page_result(self):
        """Tests that the combined page count and results object is result as expected
        """

        result = self.repo_group_repository.filter_paged_result(page_size=1)
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["page_size"] == 1
        assert result["total"] > 0

        page_0_repo_group_name = result["items"][0].name

        result = self.repo_group_repository.filter_paged_result(page=2, page_size=1)
        page_1_repo_group_name = result["items"][0].name

        assert page_0_repo_group_name != page_1_repo_group_name

    def test_get_first(self):
        """Tests that a single repo group is returned when a fitler is used
        """

        result = self.repo_group_repository.first(**{"name": "repo group 1"})
        assert isinstance(result, RepoGroup)

    def test_get_by_id(self):
        """Tests that requesting a repo by ID returns the expected result
        """

        # First find a repo based on name incase any messing around
        # has been done with a test db that could cause IDs to not be
        # an expected value
        result = self.repo_group_repository.filter(**{"name": "repo group 1"})
        repo_group_id = result[0].id

        result = self.repo_group_repository.get_by_id(repo_group_id)
        assert isinstance(result, RepoGroup)
        assert result.id == repo_group_id

    def test_add(self):
        """Tests that a repo group instnace is returned when the add method is called
        db is flushed to generated an id and then rolled back
        """

        repo_group = self.repo_group_repository.add(**{
            "name": "no filter"
        })
        self.db.flush()

        assert isinstance(repo_group, RepoGroup)
        assert repo_group.id is not None
        self.db.rollback()

    def test_bulk_add(self):
        """Tests that adding a list of repo groups, returns the new objects
        db is flushed to generate repo ids and then rolled back once assertions passed
        """

        repo_groups = self.repo_group_repository.bulk_add([
            {
                "name": "test repo group 1",
                "regex_include": "regex1"
            },
            {
                "name": "test repo group 2",
                "regex_include": "regex2"
            }
        ])
        self.db.flush()
        assert isinstance(repo_groups, list)

        count = 0
        for repo_group in repo_groups:
            count += 1
            assert repo_group.id is not None
            assert repo_group.name == f"test repo group {count}"

    def test_update(self):
        """Tests updating a repo is successful. This test works by adding a repo group
        flushing the db, updating the repo group, flushing the db again and then retrieving
        the updated repo group. Once assertions have passed the db is rolled back
        """

        repo_group = self.repo_group_repository.add(**{
            "name": "repo group to update"
        })
        self.db.flush()

        repo_group_id = repo_group.id

        self.repo_group_repository.update(repo_group, **{"regex_include": "update"})
        self.db.flush()

        repo_group = self.repo_group_repository.get_by_id(repo_group.id)
        assert repo_group.regex_include == "update"
        self.db.rollback()

    def test_bulk_update(self):
        """Tests bulk updating of repo groups. Test works by creating two repo groups to update
        and flushing the db. The bulk update is called and then once assertions have passed the
        db is rolledback
        """

        repo_groups_for_update = self.repo_group_repository.bulk_add([
            {
                "name": "repo group to update 1",
            },
            {
                "name": "repo group to update 2"
            }
        ])
        self.db.flush()

        update_repo_group_config = []
        for repo_group in repo_groups_for_update:
            update_repo_group_config.append({"id": repo_group.id, "regex_exclude": "reg1"})

        self.repo_group_repository.bulk_update(update_repo_group_config)
        for rg in repo_groups_for_update:
            repo_group = self.repo_group_repository.get_by_id(rg.id)
            assert repo_group.regex_exclude == "reg1"

        self.db.rollback()

    def test_delete(self):
        """Tests removing a repo group from the db. A repo group is created and the db flushed.
        The repo group is then removed from the DB and once all assertions have passed the db
        is rolledback
        """

        repo_group = self.repo_group_repository.add(**{
            "name": "repoi group to delete"
        })
        self.db.flush()

        repo_group_id = repo_group.id

        self.repo_group_repository.delete(repo_group)
        self.db.flush()

        repo_group = self.repo_group_repository.get_by_id(repo_group_id)
        assert repo_group is None
        self.db.rollback()

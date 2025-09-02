"""Tests the snapshotter
"""

import pytest

from datetime import datetime
from mock import patch
from pulp3_bindings.pulp3 import Pulp3Client
from pulp3_bindings.pulp3.resources import (
    DebRemote, DebRepository, RpmRepository, Task as Pulp3Task
)

from pulp_manager.app.database import session, engine
from pulp_manager.app.exceptions import PulpManagerSnapshotError
from pulp_manager.app.models import Repo, PulpServer, PulpServerRepo, Task
from pulp_manager.app.services import Snapshotter
from pulp_manager.app.repositories import (
    PulpServerRepository, RepoRepository, PulpServerRepoRepository, TaskRepository,
    TaskStageRepository
)


class TestSnapshotter:
    """Test class for snapshotter
    """

    @classmethod
    def setup_class(cls):
        """Add some additional sample data to be used for tests
        """

        db = session()
        pulp_server_repository = PulpServerRepository(db)
        repo_repository = RepoRepository(db)
        pulp_server_repo_repository = PulpServerRepoRepository(db)

        pulp_server = pulp_server_repository.add(**{
            "name": "pulp_server.domain.local",
            "username": "username",
            "vault_service_account_mount": "vault-service-accounts",
            "snapshot_supported": True,
            "max_concurrent_snapshots": 2
        })

        repo1 = repo_repository.add(**{
            "name": "ext-test-rpm-repo",
            "repo_type": "rpm"
        })

        repo2 = repo_repository.add(**{
            "name": "existing-snap-ext-test-rpm-repo",
            "repo_type": "rpm"
        })

        pulp_server_repo1 = pulp_server_repo_repository.add(**{
            "pulp_server": pulp_server,
            "repo": repo1,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
        })

        pulp_server_repo2 = pulp_server_repo_repository.add(**{
            "pulp_server": pulp_server,
            "repo": repo2,
            "repo_href": "/pulp/api/v3/repositories/rpm/rpm/456"
        })

        db.commit()

        cls.pulp_server_id = pulp_server.id
        cls.pulp_server_repo1_id = pulp_server_repo1.id
        cls.pulp_server_repo2_id = pulp_server_repo2.id

        db.close()
        engine.dispose()

    @patch("pulp_manager.app.services.pulp_manager.new_pulp_client")
    @patch("pulp_manager.app.services.pulp_manager.PulpManager._get_deb_signing_service")
    @patch("pulp_manager.app.services.snapshotter.new_pulp_client")
    def setup_method(self, method, mock_new_pulp_client, mock_get_deb_signing_service,
            mock_pulp_manager_new_pulp_client):
        """Setup fake repository and mocks
        """

        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")

        mock_new_pulp_client.side_effect = new_pulp_client
        mock_pulp_manager_new_pulp_client.side_effect = new_pulp_client
        mock_get_deb_signing_service.return_value = "/pulp/api/v3/signing-services/123"

        self.db = session()
        self.pulp_server_repo_repository = PulpServerRepoRepository(self.db)
        self.task_repository = TaskRepository(self.db)
        self.task_stage_repository = TaskStageRepository(self.db)
        self.snapshotter = Snapshotter(self.db, "pulp_server.domain.local")

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()
        engine.dispose()

    def test_get_supported_snapshot_repo_type(self):
        """Tests that a list returned containing the repo types that are supported for snapshot
        """

        supported_repos = self.snapshotter.get_supported_snapshot_repo_type()
        assert isinstance(supported_repos, list)
        for repo_type in supported_repos:
            assert isinstance(repo_type, str)

    @patch("pulp_manager.app.services.reconciler.PulpReconciler.reconcile", autospec=True)
    def test_do_reconcile(self, mock_reconcile):
        """Tests when do reconcile is called, if there are no errors it completes
        successfully
        """

        self.snapshotter._do_reconcile

    @patch("pulp_manager.app.services.snapshotter.get_repo", autospec=True)
    @patch("pulp_manager.app.services.PulpManager.create_or_update_repository", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.get_all_repos", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.copy_repo", autospec=True)
    def test_start_snapshot(self, mock_copy_repo, mock_get_all_repos,
            mock_create_or_update_repository, mock_get_repo):
        """Tests that when a snapshot is started, a PulpManager Task entity is returned
        containing the details about the snapshot task
        """

        mock_get_repo.return_value = RpmRepository(**{
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/123",
            "name": "ext-test-rpm-repo"
        })

        def create_or_update_repository(pulp_manager_self, name, description, repo_type):
            """Side effect for create_or_update_repository. Fiddles with the mock entites
            to save mocking out a load of extra calls, and to make it easier to set values
            """

            self.entities.append(
                Repo(**{"id": 2, "name": "my-snap-ext-test-rpm-repo", "repo_type": "rpm"})
            )

            fake_snapshot_pulp_server_repo = PulpServerRepo(**{
                "id": 2,
                "pulp_server_id": 1,
                "repo_id": 2,
                "repo_href": "/pulp/api/v3/repositories/rpm/rpm/456",
                "distribution_href": "/pulp/api/v3/distributions/rpm/rpm/456"
            })

            self.entities.append(fake_snapshot_pulp_server_repo)
            return fake_snapshot_pulp_server_repo


        mock_create_or_update_repository.side_effect = create_or_update_repository
        mock_get_all_repos.return_value = [RpmRepository(**{
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/456",
            "name": "my-snap-ext-test-rpm-repo"
        })]

        mock_copy_repo.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-copy",
            "logging_cid": "123"
        })

        repo = self.pulp_server_repo_repository.first(**{"id": self.pulp_server_repo1_id})

        result = self.snapshotter._start_snapshot(repo, "my-snap")
        assert isinstance(result, Task)
        assert result.name == "snapshot ext-test-rpm-repo"

    @patch("pulp_manager.app.services.snapshotter.get_repo", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.PulpManager.create_publication_from_repo_version", autospec=True)
    def test_start_publication(self, mock_create_publication_from_repo_version, mock_get_repo):
        """Tests that when _start_publication is called, if everything is fine no errors are thrown
        """

        mock_get_repo.return_value = RpmRepository(**{
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/123",
            "name": "my-snap-ext-test-rpm-repo"
        })
        task = self.task_repository.add(**{
            "name": "snapshot ext-test-rpm-repo",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        self.db.commit()

        mock_create_publication_from_repo_version.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-publish",
            "logging_cid": "123"
        })

        self.snapshotter._start_publication(task)

    @patch("pulp_manager.app.services.snapshotter.get_remote", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.get_repo", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.PulpManager.create_publication_from_repo_version", autospec=True)
    def test_start_publication_deb_none_flat(self, mock_create_publication_from_repo_version,
            mock_get_repo, mock_get_remote):
        """Tests that when _start_publication is called, and the repo isn't flat the args are called to
        start publication
        """

        def mock_get_repo_side_effect(pulp_client, href, params=None):
            # The source repo is the first that is being returned in the if statement
            if href == "/pulp/api/v3/repositories/deb/apt/123":
                return DebRepository(**{
                    "pulp_href": "/pulp/api/v3/repositories/deb/apt/123",
                    "name": "deb-none-flat",
                    "remote": "/pulp/api/v3/remotes/deb/apt/123"
                })
            else:
                return DebRepository(**{
                    "pulp_href": "/pulp/api/v3/repositories/deb/apt/456",
                    "name": "snap-deb-none-flat"
                })

        mock_get_repo.side_effect = mock_get_repo_side_effect

        mock_get_remote.return_value = DebRemote(**{
            "pulp_href": "/pulp/api/v3/remotes/deb/apt/123",
            "name": "deb-none-flat",
            "url": "https://deb-remote.domain.local",
            "policy": "immediate", 
            "distributions": "focal"
        })

        mock_create_publication_from_repo_version.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-publish",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot deb-none-flat",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "source_repo_href": "/pulp/api/v3/repositories/deb/apt/123",
                "dest_repo_href": "/pulp/api/v3/repositories/deb/apt/456"
            }
        })
        self.db.commit()

        self.snapshotter._start_publication(task)
        mock_create_publication_from_repo_version_call_args, mock_create_publication_from_repo_version_call_kwargs = mock_create_publication_from_repo_version.call_args

        # Check is_flat_repo is false, checking fourth arg, as need to account for self
        assert mock_create_publication_from_repo_version_call_args[3] == False

    @patch("pulp_manager.app.services.snapshotter.get_remote", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.get_repo", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.PulpManager.create_publication_from_repo_version", autospec=True)
    def test_start_publication_deb_flat(self, mock_create_publication_from_repo_version,
            mock_get_repo, mock_get_remote):
        """Tests that when _start_publication is called, and the repo isn't flat the args are called to
        start publication
        """

        def mock_get_repo_side_effect(pulp_client, href, params=None):
            # The source repo is the first that is being returned in the if statement
            if href == "/pulp/api/v3/repositories/deb/apt/123":
                return DebRepository(**{
                    "pulp_href": "/pulp/api/v3/repositories/deb/apt/123",
                    "name": "deb-none-flat",
                    "remote": "/pulp/api/v3/remotes/deb/apt/123"
                })
            else:
                return DebRepository(**{
                    "pulp_href": "/pulp/api/v3/repositories/deb/apt/456",
                    "name": "snap-deb-none-flat"
                })

        mock_get_repo.side_effect = mock_get_repo_side_effect

        mock_get_remote.return_value = DebRemote(**{
            "pulp_href": "/pulp/api/v3/remotes/deb/apt/123",
            "name": "deb-flat",
            "url": "https://deb-remote.domain.local",
            "policy": "immediate", 
            "distributions": "/"
        })

        mock_create_publication_from_repo_version.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-publish",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot deb-none-flat",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "source_repo_href": "/pulp/api/v3/repositories/deb/apt/123",
                "dest_repo_href": "/pulp/api/v3/repositories/deb/apt/456"
            }
        })
        self.db.commit()

        self.snapshotter._start_publication(task)
        mock_create_publication_from_repo_version_call_args, mock_create_publication_from_repo_version_call_kwargs = mock_create_publication_from_repo_version.call_args

        # Check is_flat_repo is True, checking fourth arg, as need to account for self
        assert mock_create_publication_from_repo_version_call_args[3] == True

    @patch("pulp_manager.app.services.snapshotter.get_task", autospec=True)
    def test_progress_snapshot_copy_still_in_progress(self, mock_get_task):
        """Tests that when a task is currently still in progress False is returned
        indicating that the _progress_snapshot needs to be called again in the future
        """

        mock_get_task.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-copy",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot ext-test-rpm-repo",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        task_stage = self.task_stage_repository.add(**{
            "name": "repo snapshot",
            "detail": {"task_href": "/pulp/api/v3/task/123"},
            "task": task
        })

        self.db.commit()

        result = self.snapshotter._progress_snapshot(task)
        assert result == False

    @patch("pulp_manager.app.services.snapshotter.get_task", autospec=True)
    def test_progress_snapshot_copy_task_failed(self, mock_get_task):
        """Tests that if the task failed on the target pulp server, then True is returned
        indicating that the task completed. The task is updated in the db with the state
        as failed
        """

        mock_get_task.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "repo-copy",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot ext-test-rpm-repo",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        task_stage = self.task_stage_repository.add(**{
            "name": "repo snapshot",
            "detail": {"task_href": "/pulp/api/v3/task/123"},
            "task": task
        })

        self.db.commit()

        mock_get_task.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "failed",
            "name": "repo-copy",
            "logging_cid": "123"
        })

        result = self.snapshotter._progress_snapshot(task)
        assert result == True
        assert task.state == "failed"

    @patch("pulp_manager.app.services.snapshotter.get_task", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._start_publication", autospec=True)
    def test_progress_snapshot_copy_start_publication(self, mock_start_publication, mock_get_task):
        """Tests that if a repo copy task has completed successfully then _start_publcation is called
        """

        mock_get_task.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "completed",
            "name": "repo-copy",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot ext-test-rpm-repo",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        task_stage = self.task_stage_repository.add(**{
            "name": "repo snapshot",
            "detail": {"task_href": "/pulp/api/v3/task/123"},
            "task": task
        })

        result = self.snapshotter._progress_snapshot(task)

        assert mock_start_publication.call_count == 1
        assert result == False


    @patch("pulp_manager.app.services.snapshotter.get_task", autospec=True)
    def test_progress_snapshot_copy_still_task_completed(self, mock_get_task):
        """Tests that when the publication has completed successfully, the task is marked as
        completed in the DB and True is returned indicating there are no more stages to progress
        for the snapshot of the repo
        """

        mock_get_task.return_value = Pulp3Task(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "completed",
            "name": "repo-publish",
            "logging_cid": "123"
        })

        task = self.task_repository.add(**{
            "name": "snapshot ext-test-rpm-repo",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        task_stage = self.task_stage_repository.add(**{
            "name": "repo publication",
            "detail": {"task_href": "/pulp/api/v3/task/123"},
            "task": task
        })

        result = self.snapshotter._progress_snapshot(task)

        assert result == True
        assert task.state == "completed"

    @patch("pulp_manager.app.services.snapshotter.sleep")
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._start_snapshot")
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._progress_snapshot", autospec=True)
    def test_do_snapshot_repos(self, mock_progress_snapshot, mock_start_snapshot, mock_sleep):
        """Tests that when a list of repos snapshot without errors _task instance variable
        on the syncher is marked as completed
        """

        def start_snapshot(repo_to_snapshot, repo_snapshot_name):
            """Side effect for the patched out _start_snapshot on the Snapshotter class
            """

            task = self.task_repository.add(**{
                "name": f"snapshot {repo_to_snapshot.name}",
                "date_started": datetime.utcnow(),
                "task_type": "repo_snapshot",
                "state": "running",
                "task_args": {
                    "source_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123",
                }
            })

            self.db.commit()
            return task

        # Need to have populated a parent snapshot task otherwise
        # method call to create child task will fail when it is adding
        # a snapshot staage
        parent_task = self.task_repository.add(**{
            "name": "snapshot repos",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        self.db.commit()
        self.snapshotter._task = parent_task

        mock_start_snapshot.side_effect = start_snapshot
        mock_progress_snapshot.return_value = True

        repos_to_snapshot = self.pulp_server_repo_repository.filter(**{
            "pulp_server_id": self.pulp_server_id
        })

        self.snapshotter._do_snapshot_repos("test-", repos_to_snapshot)

        assert mock_start_snapshot.call_count == 2
        assert mock_progress_snapshot.call_count == 2
        assert self.snapshotter._task.state == "completed"

        # reset _task
        self.snapshotter._task = None

    @patch("pulp_manager.app.services.snapshotter.sleep")
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._start_snapshot")
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._progress_snapshot", autospec=True)
    def test_do_snapshot_repos_fail(self, mock_progress_snapshot, mock_start_snapshot, mock_sleep):
        """Tests that if a repo errors during the snapshot process, the _task instnace variable is
        marked as failed
        """

        def start_snapshot(repo_to_snapshot, repo_snapshot_name):
            """Side effect for the patched out _start_snapshot on the Snapshotter class
            """

            # Fail on second repo in sample data
            if repo_to_snapshot.id == self.pulp_server_repo2_id:
                raise Exception("error")

            task = self.task_repository.add(**{
                "name": f"snapshot {repo_to_snapshot.name}",
                "date_started": datetime.utcnow(),
                "task_type": "repo_snapshot",
                "state": "running",
                "task_args": {
                    "source_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123",
                }
            })

            self.db.commit()
            return task

        mock_start_snapshot.side_effect = start_snapshot
        mock_progress_snapshot.return_value = True
        repos_to_snapshot = self.pulp_server_repo_repository.filter(**{
            "pulp_server_id": self.pulp_server_id
        })

        # Need to have populated a parent snapshot task otherwise
        # method call to create child task will fail when it is adding
        # a snapshot staage
        parent_task = self.task_repository.add(**{
            "name": "snapshot repos",
            "task_type": "repo_snapshot",
            "state": "running",
            "date_started": datetime.utcnow(),
            "task_args": {
                "dest_repo_href": "/pulp/api/v3/repositories/rpm/rpm/123"
            }
        })
        self.db.commit()
        self.snapshotter._task = parent_task
        self.snapshotter._do_snapshot_repos("test-", repos_to_snapshot)

        assert mock_start_snapshot.call_count == 2
        assert mock_progress_snapshot.call_count == 1
        assert self.snapshotter._task.state == "failed"

        # reset _task
        self.snapshotter._task = None

    def test_snapshot_allowed_ok(self):
        """Tests when then are no repos that match the snapshot prefix no error is thrown
        """

        self.snapshotter._snapshot_allowed("this-does-not-exist")

    def test_snapshot_allowed_fail(self):
        """Tests when then are repos that match the snapshot prefix an error is thrown
        """

        with pytest.raises(PulpManagerSnapshotError):
            self.snapshotter._snapshot_allowed("existing-snap")

    @patch("pulp_manager.app.services.snapshotter.Snapshotter._do_reconcile", autospec=True)
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._do_snapshot_repos", autospec=True)
    def test_snapshot_repos(self, mock_do_snapshot_repos, mock_do_reconcile):
        """Tests that if no errors are raised during the snapshoting creation function completes
        successfully
        """

        self.snapshotter.snapshot_repos(snapshot_prefix="my-test", regex_include="^ext-")

    @patch("pulp_manager.app.services.snapshotter.Snapshotter._do_reconcile", side_effect=Exception, autospec=True)
    @patch("pulp_manager.app.services.snapshotter.Snapshotter._do_snapshot_repos", autospec=True)
    def test_snapshot_repos_fail(self, mock_do_snapshot_repos, mock_do_reconcile):
        """Tests that if errors are raised during the snapshoting creation exception rasied and
        task is marked as failed
        """

        with pytest.raises(Exception):
            self.snapshotter.snapshot_repos(snapshot_prefix="my-test", regex_include="^ext-")

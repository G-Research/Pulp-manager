"""Runs tests on the remove content task
"""

from datetime import datetime
import pytest
from mock import patch

from pulp3_bindings.pulp3 import Pulp3Client
from pulp3_bindings.pulp3.resources import RpmRepository, RpmRemote, Task as PulpTask

from pulp_manager.app.database import session, engine
from pulp_manager.app.exceptions import PulpManagerPulpTaskError
from pulp_manager.app.models import PulpServer, Repo, PulpServerRepo, Task
from pulp_manager.app.tasks.remove_content_task import remove_repo_content
from pulp_manager.app.repositories import (TaskRepository)

class TestRemoveContentTask:
    """Tests for removing content from a repo
    """


    @patch("pulp_manager.app.tasks.remove_content_task.new_pulp_client")
    @patch("pulp_manager.app.tasks.remove_content_task.get_remote")
    @patch("pulp_manager.app.tasks.remove_content_task.get_repo")
    @patch("pulp_manager.app.tasks.remove_content_task.modify_repo")
    @patch("pulp_manager.app.tasks.remove_content_task.get_task")
    @patch("pulp_manager.app.tasks.remove_content_task.PulpManager", autospec=True)
    @patch("pulp_manager.app.tasks.remove_content_task.sleep")
    def test_remove_repo_content_ok(self, mock_sleep, mock_pulp_manager, mock_get_task,
            mock_modify_repo, mock_get_repo, mock_get_remote, mock_new_pulp_client):
        """When there are no errors at any stages the remove repo content task should complete succesffully
        """

        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")


        def get_task(client: Pulp3Client, href: str):
            return PulpTask(**{
                "pulp_href": href,
                "pulp_created": datetime.utcnow(),
                "state": "completed",
                "name": "task",
                "logging_cid": "log123",
                "created_resources": ["/pulp/api/v3/repositories/rpm/rpm/123/versions/5"] if "123" in href else []
            })

        mock_new_pulp_client.side_effect = new_pulp_client
        mock_get_task.side_effect = get_task

        mock_get_remote.return_value = RpmRemote(**{
            "pulp_href": "/pulp/api/v3/remotes/rpm/rpm/123",
            "name": "test-remote",
            "url": "https://rpm.remote.local/",
            "policy": "immediate"
        })
        mock_get_repo.return_value = RpmRepository(**{
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/123",
            "name": "test-remote",
            "remote": "/pulp/api/v3/remotes/rpm/rpm/123",
            "latest_version_href": "/pulp/api/v3/repositories/rpm/rpm/123/versions/1"
        })

        mock_modify_repo.return_value = PulpTask(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "task",
            "logging_cid": "log123"
        })
 
        mock_pulp_manager.return_value.create_publication_from_repo_version.return_value = PulpTask(**{
            "pulp_href": "/pulp/api/v3/tasks/456",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "task",
            "logging_cid": "log123"
        })

        db = session()

        task = TaskRepository(db).add(**{
            "name": "dummy task remove content ok",
            "task_type_id": 1,
            "state_id": 1,
            "task_args": {"arg": "val"}
        })
        db.commit()

        remove_repo_content(
            "pulpserver1.domain.local", "repo1", "/pulp/api/v3/packages/rpm/content/123",
            task.id, False
        )

        db.close()
        engine.dispose()

    @patch("pulp_manager.app.tasks.remove_content_task.new_pulp_client")
    @patch("pulp_manager.app.tasks.remove_content_task.get_remote")
    @patch("pulp_manager.app.tasks.remove_content_task.get_repo")
    @patch("pulp_manager.app.tasks.remove_content_task.modify_repo")
    @patch("pulp_manager.app.tasks.remove_content_task.get_task")
    @patch("pulp_manager.app.tasks.remove_content_task.PulpManager", autospec=True)
    @patch("pulp_manager.app.tasks.remove_content_task.sleep")
    def test_remove_repo_content_pulp_task_fail(self, mock_sleep, mock_pulp_manager, mock_get_task,
            mock_modify_repo, mock_get_repo, mock_get_remote, mock_new_pulp_client):
        """Tests that if a pulp task failes PulpManagerPulpTaskError is raised
        """

        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")


        def get_task(client: Pulp3Client, href: str):
            return PulpTask(**{
                "pulp_href": href,
                "pulp_created": datetime.utcnow(),
                "state": "failed",
                "name": "task",
                "logging_cid": "log123",
                "created_resources": []
            })

        mock_new_pulp_client.side_effect = new_pulp_client
        mock_get_task.side_effect = get_task

        mock_get_remote.return_value = RpmRemote(**{
            "pulp_href": "/pulp/api/v3/remotes/rpm/rpm/123",
            "name": "test-remote",
            "url": "https://rpm.remote.local/",
            "policy": "immediate"
        })
        mock_get_repo.return_value = RpmRepository(**{
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/123",
            "name": "test-remote",
            "remote": "/pulp/api/v3/remotes/rpm/rpm/123",
            "latest_version_href": "/pulp/api/v3/repositories/rpm/rpm/123/versions/1"
        })

        mock_modify_repo.return_value = PulpTask(**{
            "pulp_href": "/pulp/api/v3/tasks/123",
            "pulp_created": datetime.utcnow(),
            "state": "running",
            "name": "task",
            "logging_cid": "log123"
        })


        db = session()

        task = TaskRepository(db).add(**{
            "name": "dummy task remove content pulp task fail",
            "task_type_id": 1,
            "state_id": 1,
            "task_args": {"arg": "val"}
        })
        db.commit()

        with pytest.raises(PulpManagerPulpTaskError):
            remove_repo_content(
                "pulpserver1.domain.local", "repo1", "/pulp/api/v3/packages/rpm/content/123",
                task.id, False
            )

        db.close()
        engine.dispose()

    @patch("pulp_manager.app.tasks.remove_content_task.new_pulp_client")
    @patch("pulp_manager.app.tasks.remove_content_task.get_repo")
    @patch("pulp_manager.app.tasks.remove_content_task.sleep")
    def test_remove_repo_content_unexpected_fail(self, mock_sleep,
            mock_get_repo, mock_new_pulp_client):
        """Tests that if a unexpected error occurs excpetion is raised
        """

        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")

        mock_new_pulp_client.side_effect = new_pulp_client
        mock_get_repo.side_effect = Exception("unexpected error")

        db = session()

        task = TaskRepository(db).add(**{
            "name": "dummy task remove content pulp task fail",
            "task_type_id": 1,
            "state_id": 1,
            "task_args": {"arg": "val"}
        })
        db.commit()

        with pytest.raises(Exception):
            remove_repo_content(
                "pulpserver1.domain.local", "repo1", "/pulp/api/v3/packages/rpm/content/123",
                2, False
            )

        db.close()
        engine.dispose()

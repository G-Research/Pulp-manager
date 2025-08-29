"""Carries out tests for v1 pulp_servers routes
"""
import fakeredis
from mock import patch
from fastapi.testclient import TestClient

from pulp_manager.app.auth.auth_handler import sign_jwt



class TestPulpServersV1Routes:
    """Testing class
    """

    def test_all(self, client: TestClient):
        """Tests that all tasks are returned 
        """

        result = client.get(client.app.url_path_for("tasks_v1:all"))
        assert result.status_code == 200
        assert result.json()["total"] > 1
        assert len(result.json()["items"]) > 1

        result = client.get(
            client.app.url_path_for("tasks_v1:all"),
            params={"state": "queued"}
        )
        assert result.status_code == 200
        assert result.json()["total"] > 1

        for task in result.json()["items"]:
            assert task["state"] == "queued"

        result = client.get(
            client.app.url_path_for("tasks_v1:all"),
            params={"task_type": "repo_sync"}
        )
        assert result.status_code == 200
        assert result.json()["total"] > 1

        for task in result.json()["items"]:
            assert task["task_type"] == "repo_sync"

    def test_get_task_types(self, client: TestClient):
        """Tests that all task types are returned
        """

        result = client.get(client.app.url_path_for("tasks_v1:task_types"))
        assert result.status_code == 200
        assert len(result.json()) > 0

    def test_get_task_states(self, client: TestClient):
        """Tests that all task states are returned
        """

        result = client.get(client.app.url_path_for("tasks_v1:task_states"))
        assert result.status_code == 200
        assert len(result.json()) > 0

    def test_get(self, client: TestClient):
        """Tests getting a task by ID returns a TaskDetail result
        """

        result = client.get(client.app.url_path_for("tasks_v1:get_task", id=1))
        assert result.status_code == 200
        assert result.json()["id"] == 1
        assert "stages" in result.json()

    def test_change_state(self, client: TestClient):
        """Tests changing the state of a task
        """

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        result = client.patch(
            client.app.url_path_for("tasks_v1:change_state", id=1),
            json = {"state": "canceled"},
            headers = {
                "Authorization": f"Bearer {signed_jwt['access_token']}"
            }
        )

        assert result.status_code == 200
        assert result.json()["id"] == 1
        assert result.json()["state"] == "canceled"

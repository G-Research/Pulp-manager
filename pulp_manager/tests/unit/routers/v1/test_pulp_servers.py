"""Carries out tests for v1 pulp_servers routes
"""
import fakeredis
from mock import patch
from fastapi.testclient import TestClient
from pulp3_bindings.pulp3 import Pulp3Client

from pulp_manager.app.auth.auth_handler import sign_jwt
from pulp_manager.app.models import PulpServer


class TestPulpServersV1Routes:
    """Testing class
    """

    def test_all(self, client: TestClient):
        """Tests that all pulp servers are returned when no filter is specified
        """

        result = client.get(client.app.url_path_for("pulp_servers_v1:all"))
        assert result.status_code == 200

        result = client.get(
            client.app.url_path_for("pulp_servers_v1:all"),
            params={"repo_sync_health_rollup": "green"}
        )
        assert result.status_code == 200
        assert len(result.json()["items"]) == 1

    def test_get_repo_health_statuses(self, client: TestClient):
        """Tests that list of repo health statuses are returned
        """

        result = client.get(client.app.url_path_for("pulp_servers_v1:repo_health_statuses"))
        assert result.status_code == 200
        assert len(result.json()) > 0

    def test_get_server_by_id(self, client: TestClient):
        """_summary_

        Args:
            client (TestClient): _description_
        """
        # Test existing server
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_by_id", id=1))
        assert result.status_code == 200
        assert result.json()["id"] == 1

        # Test non-existing server
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_by_id", id=1000))
        assert result.status_code == 404

    def test_get_repos_by_server_id(self, client: TestClient):
        """Tests retrieving repos for a pulp server returns the correct results
        """

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repos_by_server_id", id=1))
        assert result.status_code == 200
        for item in result.json()["items"]:
            assert item["pulp_server_id"] == 1
        assert result.json()["total"] > 1

    def test_get_repos_by_server_id_filter(self, client: TestClient):
        """Tests retrieving repos for a pulp server with filtering returns the correct results
        """

        result = client.get(
            client.app.url_path_for("pulp_servers_v1:get_repos_by_server_id", id=1),
            params={"name__match": "repo"}
        )

        assert result.status_code == 200
        assert result.json()["items"][0]["pulp_server_id"] == 1
        assert result.json()["total"] == 2

        result = client.get(
            client.app.url_path_for("pulp_servers_v1:get_repos_by_server_id", id=1),
            params={"name__match": "repo", "repo_sync_health": "green"}
        )

        assert result.status_code == 200
        for item in result.json()["items"]:
            assert item["pulp_server_id"] == 1
        assert result.json()["total"] == 1

    def test_get_repo_by_repo_id(self, client: TestClient):
        """_summary_
        """
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_by_repo_id", id=1, repo_id=2))
        assert result.status_code == 200
        assert result.json()["pulp_server_id"] == 1
        assert result.json()["repo_id"] == 2

        #testing no existent server id
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_by_repo_id", id=1000, repo_id=1))
        assert result.status_code == 404

        #testing no existent repo id
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_by_repo_id", id=1, repo_id=1000))
        assert result.status_code == 404

    @patch("pulp_manager.app.services.pulp_manager.new_pulp_client")
    @patch("pulp_manager.app.services.pulp_manager.PulpManager.find_repo_package_content")
    @patch("pulp_manager.app.services.pulp_manager.PulpManager._get_deb_signing_service")
    def test_find_package_content(self, mock_get_deb_signing_service,
            mock_find_repo_package_content, mock_new_pulp_client, client: TestClient):
        """Tests that what package content information is requested from a repo, the
        data is returned
        """

        def new_pulp_client(pulp_server: PulpServer):
            return Pulp3Client(pulp_server.name, username=pulp_server.username, password="test")

        mock_new_pulp_client.side_effect = new_pulp_client
        mock_find_repo_package_content.return_value = [
            {
                "name": "package",
                "pulp_href": "/pulp/api/v3/content/rpm/packages/123",
                "sha256": "12345",
                "version": "2"
            },
            {
                "name": "package",
                "pulp_href": "/pulp/api/v3/content/rpm/packages/456",
                "sha256": "678910",
                "version": "3"
            }
        ]

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        result = client.post(
            client.app.url_path_for("pulp_servers_v1:find_package_content", id=1, repo_id=1),
            json={
                "name": "package"
            },
            headers={
                "Authorization": f"Bearer {signed_jwt['access_token']}"
            }
        )

        assert result.status_code == 201
        assert len(result.json()) == 2

    def test_remove_repo_content(self, client: TestClient, fake_redis: fakeredis):
        """Checks that a repos content removal is successfully scheduled and a task object returned
        """

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        with patch("pulp_manager.app.job_manager.Redis", return_value=fake_redis):
            result = client.post(
                client.app.url_path_for("pulp_servers_v1:remove_package_content", id=1, repo_id=1),
                json={
                    "content_href": "/pulp/api/v3/packages/rpm/content/123",
                    "max_runtime": "10m"
                },
                headers={
                    "Authorization": f"Bearer {signed_jwt['access_token']}"
                }
            )
            assert result.status_code == 201

    def test_get_tasks_for_repo(self, client: TestClient):
        """Tests retrieving all tasks for a repo
        """

        pulp_server_repo_result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_by_repo_id", id=1, repo_id=1))
        pulp_server_repo_id = pulp_server_repo_result.json()["id"]

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_tasks_for_repo", id=1, repo_id=1))
        assert result.status_code == 200
        assert result.json()["total"] >= 1

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_tasks_for_repo", id=1000, repo_id=1))
        assert result.status_code == 404

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_tasks_for_repo", id=1, repo_id=1000))
        assert result.status_code == 404

    def test_get_repo_groups_by_server_id(self, client: TestClient):
        """test for get repo groups
        """
        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_groups_for_server", id=1))
        assert result.status_code == 200
        assert result.json()["total"] >= 1

        result = client.get(
            client.app.url_path_for("pulp_servers_v1:get_repo_groups_for_server", id=1),
            params={"name__match": "repo group"}
        )
        assert result.status_code == 200
        assert result.json()["total"] == 2

        for item in result.json()["items"]:
            assert item["pulp_server_id"] == 1


    def test_get_repo_groups_by_group_id(self, client: TestClient):
        """test for get repo groups
        """

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_groups_for_server_by_group_id", id=1, repo_group_id=2))
        assert result.status_code == 200
        assert result.json()["pulp_server_id"] == 1
        assert result.json()["repo_group_id"] == 2

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_groups_for_server_by_group_id", id=1000, repo_group_id=2))
        assert result.status_code == 404

        result = client.get(client.app.url_path_for("pulp_servers_v1:get_repo_groups_for_server_by_group_id", id=1, repo_group_id=2000))
        assert result.status_code == 404

    def test_snapshot_repos_ok(self, client: TestClient, fake_redis: fakeredis):
        """Tests that when a snapshot request is submitted for a valid pulp server a
        task object is returned
        """

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        with patch("pulp_manager.app.job_manager.Redis", return_value=fake_redis):
            result = client.post(
                client.app.url_path_for("pulp_servers_v1:snapshot_repos", id=1),
                json={
                    "max_runtime": "12h",
                    "snapshot_prefix": "test-snap",
                    "allow_snapshot_reuse": True,
                    "regex_include": "^ext-"
                },
                headers={
                    "Authorization": f"Bearer {signed_jwt['access_token']}"
                }
            )
            assert result.status_code == 201
            task = result.json()
            assert task["task_args"]["max_runtime"] == "12h"
            assert task["task_args"]["snapshot_prefix"] == "snap-test-snap"
            assert task["task_args"]["allow_snapshot_reuse"] == True
            assert task["task_args"]["regex_include"] == "^ext-"
            assert task["task_args"]["regex_exclude"] is None

    def test_sync_repos_ok(self, client: TestClient, fake_redis: fakeredis):
        """Tests that when sync repos is called with correct arguments a task object is returned
        """

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        with patch("pulp_manager.app.job_manager.Redis", return_value=fake_redis):
            result = client.post(
                client.app.url_path_for("pulp_servers_v1:sync_repos", id=1),
                json={
                    "max_runtime": "12h",
                    "max_concurrent_syncs": 2,
                    "regex_include": "^ext-"
                },
                headers={
                    "Authorization": f"Bearer {signed_jwt['access_token']}"
                }
            )
            assert result.status_code == 201
            task = result.json()
            assert task["task_args"]["max_runtime"] == "12h"
            assert task["task_args"]["max_concurrent_syncs"] == 2
            assert task["task_args"]["regex_include"] == "^ext-"

    def test_sync_repos_fail(self, client: TestClient, fake_redis: fakeredis):
        """Tests that when sync is requested with max concurrent syncs set to 0, error thrown
        """

        # This endpoint requires auth so need to generated a valid JWT
        signed_jwt = sign_jwt("fake_user", ["pulpmaster-rw"])

        with patch("pulp_manager.app.job_manager.Redis", return_value=fake_redis):
            result = client.post(
                client.app.url_path_for("pulp_servers_v1:sync_repos", id=1),
                json={
                    "max_runtime": "12h",
                    "max_concurrent_syncs": 0,
                    "regex_include": "^ext-"
                },
                headers={
                    "Authorization": f"Bearer {signed_jwt['access_token']}"
                }
            )
            assert result.status_code == 400

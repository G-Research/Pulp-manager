"""Carries out tests for v1 pulp_servers routes
"""
import fakeredis
from mock import patch
from fastapi.testclient import TestClient

from pulp_manager.app.services import RQInspector
from pulp_manager.app.schemas import Queue, Job, JobDetailed


class TestPulpServersV1Routes:
    """Testing class, fake redis content is generated from conftest.py, and the
    get_redis_connection dependency is overrided so the API doesn't try and talk
    to a real redis server
    """

    def test_get_all_queues(self, client: TestClient):
        """Tests that all queue names are returned
        """

        result = client.get(client.app.url_path_for("rq_jobs_v1:all_queues"))
        assert result.status_code == 200
        items = result.json()
        assert len(items) == 1
        assert "default" in items

    def test_get_queue(self, client: TestClient):
        """Tests that stats about the requested queue are returned
        """

        result = client.get(client.app.url_path_for("rq_jobs_v1:get_queue", **{"name": "default"}))
        assert result.status_code == 200
        queue_json = result.json()
        # Create object from JSON to make sure got vlaid type back
        Queue(**queue_json)

    def test_get_queue_scheduled_jobs(self, client: TestClient):
        """Tests that a list of jobs in the scheduler queue for the speicified queue are returned
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_scheduled", **{"name": "default"})
        )
        
        assert result.status_code == 200
        result_json = result.json()

        assert len(result_json["items"]) == 1

    def test_get_queue_queued_jobs(self, client: TestClient):
        """Tests api route for retrieving list of queued jobs in specified queue
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_queued", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        assert len(result_json["items"]) == 0

    def test_get_queue_deferred_jobs(self, client: TestClient):
        """Tests api route for retrieving list of deferred jobs in specified queue
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_deferred", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        assert len(result_json["items"]) == 0

    def test_get_queue_started_jobs(self, client: TestClient):
        """Tests api route for retrieving list of started jobs in specified queue
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_started", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        assert len(result_json["items"]) == 0

    def test_get_queue_finished_jobs(self, client: TestClient):
        """Tests api route for retrieving list of finished jobs in specified queue
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_finished", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        assert len(result_json["items"]) == 2

    def test_get_queue_failed_jobs(self, client: TestClient):
        """Tests api route for retrieving list of failed jobs in specified queue
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_failed", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        assert len(result_json["items"]) == 1

    def test_get_job(self, client: TestClient):
        """Tests that job information can be retreived vai the job endpoint
        """

        result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_queue_jobs_finished", **{"name": "default"})
        )
        assert result.status_code == 200
        result_json = result.json()
        job_id = result_json["items"][0]["id"]
        job_result = client.get(client.app.url_path_for(
            "rq_jobs_v1:get_job", **{"id": job_id})
        )

"""Tests for ensuring jobs are correct added to redis
"""

import pytest
import fakeredis
from rq import Queue
from rq_scheduler import Scheduler

from pulp_manager.app.exceptions import PulpManagerInvalidPageSize, PulpManagerEntityNotFoundError
from pulp_manager.app.services import RQInspector


# Test jobs to queue into fake redis
def success_job():
    return True

def fail_job():
    raise Exception("oh no!")


class TestJobManager:
    """Tests for job manager functions
    """

    def setup_method(self):
        """Replace redis with fakeredis
        """

        fake_redis =  fakeredis.FakeStrictRedis()

        # Generate some success and fail jobs
        # is_async=False instructs rq to instantly perform the job in the same thread instead of
        # dispatching it to the workers
        queue = Queue(name="default", is_async=False, connection=fake_redis)
        scheduler = Scheduler(queue=queue, connection=fake_redis)

        job = queue.enqueue(success_job)
        job = queue.enqueue(success_job)
        job = queue.enqueue(fail_job)

        # This menas a worker will be required to proces the job which will then leave it
        # in a scheduled state
        queue = Queue(name="default", is_async=True, connection=fake_redis)
        scheduler.cron(
            "0 0 * * *",
            func=success_job,
            queue_name="default"
        )

        self.rq_inspector = RQInspector(fake_redis)

    def test_check_page_size_ok(self):
        """Tests that when a page size given is not larger than the maximum then
        no excpetion is thrown
        """

        self.rq_inspector._check_page_size(10)

    def test_check_page_size_fail(self):
        """Tests when a page size is larger tha nthe maximum then an exception is thrown
        """

        with pytest.raises(PulpManagerInvalidPageSize):
            self.rq_inspector._check_page_size(100)

    def test_get_queues(self):
        """Tests that a the correct number of queue is returned
        """

        queues = self.rq_inspector.get_queues()
        assert len(queues) == 1

    def test_get_queue(self):
        """Checks that a queue that exists is returned
        """

        queue = self.rq_inspector.get_queue("default")
        assert queue is not None

    def test_get_queue_fail(self):
        """Checks that when a queue doesn't exist an exception is raised
        """

        with pytest.raises(PulpManagerEntityNotFoundError):
            self.rq_inspector.get_queue("defaulting")

    def test_get_queue_stats(self):
        """Checks the correct stats about a queue are returned
        """

        stats = self.rq_inspector.get_queue_stats("default")
        assert stats["name"] == "default"
        assert stats["queued_jobs"] == 0
        assert stats["deferred_jobs"] == 0
        assert stats["started_jobs"] == 0
        assert stats["finished_jobs"] == 2
        assert stats["failed_jobs"] == 1

    def test_get_queue_registry_jobs(self):
        """Tests that the correct jobs for the queue are returned
        """

        result = self.rq_inspector.get_queue_registry_jobs(
            "default", "finished_job_registry", 1, 8
        )
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 8
        assert result["total"] == 2

    def test_get_job_id(self):
        """Tests when a valid job id is given a dict with job information is returned
        """
        result = self.rq_inspector.get_queue_registry_jobs(
            "default", "finished_job_registry", 1, 8
        )
        job = self.rq_inspector.get_job(result["items"][0]["id"])

        assert isinstance(job, dict)
        assert job["id"] == result["items"][0]["id"]
        assert "args" in job
        assert "meta" in job
        assert "status" in job
        assert "enqueued_at" in job
        assert "started_at" in job
        assert "ended_at" in job
        assert "result_ttl" in job
        assert "ttl" in job
        assert "timeout" in job

        # Test getting detailed info
        job = self.rq_inspector.get_job(result["items"][0]["id"], True)
        assert "exc_info" in job

    def test_get_scheduled_jobs(self):
        """Tests the jobs are returned from the scheduler queue
        """

        result = self.rq_inspector.get_scheduled_jobs("default")
        assert len(result["items"]) == 1

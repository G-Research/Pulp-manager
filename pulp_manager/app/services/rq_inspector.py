"""Class used for inspecting RQ. Isn't designed for doing any manipulations,
just gives some basic info. RQ-dashboard gives more detailed information
"""

from redis import Redis
from rq import Queue
from rq.job import Job
from rq_scheduler import Scheduler

from pulp_manager.app.config import CONFIG
from pulp_manager.app.exceptions import PulpManagerEntityNotFoundError, PulpManagerInvalidPageSize
from pulp_manager.app.services.base import PulpManagerService


REDIS_QUEUE_IDENTIFIER = "rq:queues"


class RQInspector(PulpManagerService):
    """Class that carries out the RQ inspection
    """

    def __init__(self, redis_conn: Redis):
        """Constructor

        :param redis: redis connection
        :type redis_conn: Redis
        """

        self._redis = redis_conn

    def _check_page_size(self, page_size: int):
        """Checks the requested page size is allowed and if not an exception is raised
        """

        if page_size > int(CONFIG["redis"]["max_page_size"]):
            raise PulpManagerInvalidPageSize(
                f"page_size larger than {page_size} not allowed for rq jobs"
            )

    def get_queues(self):
        """Returns a list of queue names

        :return: List[str]
        """
        if not self._redis.exists(REDIS_QUEUE_IDENTIFIER):
            return []

        redis_queues = []
        for queue_name in self._redis.smembers(REDIS_QUEUE_IDENTIFIER):
            redis_queues.append(queue_name.decode().replace("rq:queue:", ""))

        return redis_queues

    def get_queue(self, name: str):
        """Returns a RQ queue object

        :param name: Name of the queue to get stats on
        :type name: str
        :return: Queue
        """

        if name not in self.get_queues():
            raise PulpManagerEntityNotFoundError(f"queue {name} not found")

        queue = Queue(name=name, connection=self._redis)
        return queue

    def get_queue_stats(self, name: str):
        """Returns a dict containing the stats about the queue

        :param name: name of the queue to get stats on
        :type name: str
        :return: dict
        """

        queue = self.get_queue(name)
        return {
            "name": name,
            "queued_jobs": len(queue.scheduled_job_registry.get_job_ids()),
            "deferred_jobs": len(queue.deferred_job_registry.get_job_ids()),
            "started_jobs": len(queue.started_job_registry.get_job_ids()),
            "finished_jobs": len(queue.finished_job_registry.get_job_ids()),
            "failed_jobs": len(queue.failed_job_registry.get_job_ids())
        }

    def _format_job(self, job: Job, detailed: bool=False):
        """Formats the given job into a dict that is comptable with the Job Schema
        """

        job_details = {
            "id": job.id,
            "args": job.args,
            "meta": job.meta,
            "status": job.get_status(),
            "enqueued_at": job.enqueued_at,
            "started_at": job.started_at,
            "ended_at": job.ended_at,
            "result_ttl": job.result_ttl,
            "ttl": job.ttl,
            "timeout": job.timeout
        }

        if detailed:
            job_details["exc_info"] = job.exc_info

        return job_details

    #pylint: disable=redefined-builtin
    def get_job(self, id: str, detailed: bool=False):
        """Returns a dict that contains information about the specified job

        :param id: id of job to retrieve information for
        :type id: int
        :param detailed: if set to true will ouput exception/output of job
        :type detailed: bool
        :return: dict
        """

        job = Job.fetch(id, connection=self._redis)
        return self._format_job(job, detailed)

    def get_queue_registry_jobs(self, name: str, registry_name: str, page: int=1,
            page_size: int=8):
        """Returns jobs in the requested registry for the queue. Where a registry name is,
        queued, deferred, started etc

        :param name: name of the queue to get registry jobs for
        :type name: str
        :param registry_name: name of the registry jobs to get
        :type registry_name: str
        :param page: page number to retrieve
        :type page: int
        :param page_size: number of jobs to return
        :type page_size: int
        :return: dict
        """

        self._check_page_size(page_size)

        queue = self.get_queue(name)
        registry = getattr(queue, registry_name)
        job_ids = registry.get_job_ids()

        start_page_num = (page - 1) * page_size
        end_page_num = start_page_num + page_size

        jobs = []
        total = 0
        if not start_page_num > (len(job_ids) - 1):
            if end_page_num > (len(job_ids) - 1):
                end_page_num = len(job_ids)

            jobs_to_get = job_ids[start_page_num:end_page_num]
            for job_id in jobs_to_get:
                jobs.append(self.get_job(job_id))
            total = len(job_ids)

        return {
            "items": jobs,
            "page": page,
            "page_size": page_size,
            "total": total
        }

    def get_scheduled_jobs(self, name: str, page: int=1, page_size: int=8):
        """Returns the jobs that the scheduler has queued in the given queue

        :param name: name of the queue to get the scheduled jobs for
        :type name: str
        :param page: page number to retrieve
        :type page: int
        :param page_size: number of jobs to return
        :type page_size: int
        :return: dict
        """

        self._check_page_size(page_size)

        queue = self.get_queue(name)
        scheduler = Scheduler(queue=queue, connection=queue.connection)
        # Schedule doesn't have a get_job_ids function and instead returns a
        # generator. We could maybe subclass the Scheduler and provide
        # our own version, but as we don't expect many jobs to be sitting
        # to be scheduled on a cron just looping over what is stored
        # and providing the list from the right indexes in the array is most
        # lukely fine
        scheduler_jobs = scheduler.get_jobs()

        start_page_num = (page - 1) * page_size
        end_page_num = start_page_num + page_size

        jobs = []
        count = 0

        for job in scheduler_jobs:
            #pylint: disable=chained-comparison
            if count >= start_page_num and count < end_page_num:
                jobs.append(self._format_job(job, False))
            count += 1

        return {
            "items": jobs,
            "page": page,
            "page_size": page_size,
            "total": count
        }

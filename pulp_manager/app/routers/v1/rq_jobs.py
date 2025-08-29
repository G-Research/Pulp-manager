"""Router for inspecting rq jobs
"""
# pylint: disable=too-many-arguments,unused-argument
from typing import List
from fastapi import APIRouter, Depends

from pulp_manager.app.schemas import Queue, Job, JobDetailed, Page
from pulp_manager.app.services import RQInspector
from pulp_manager.app.redis_connection import get_redis_connection
from pulp_manager.app.route import LoggingRoute


rq_jobs_v1_router = APIRouter(
    prefix="/v1/rq_jobs",
    tags=["rq_jobs"],
    responses={404: {"description": "Not found"}},
    route_class=LoggingRoute
)


@rq_jobs_v1_router.get("/queues", name="rq_jobs_v1:all_queues", response_model=List[str])
def get_all_queues(redis: get_redis_connection = Depends()):
    """Returns list of RQ queue names that exist
    """

    return RQInspector(redis).get_queues()


@rq_jobs_v1_router.get("/queues/{name}", name="rq_jobs_v1:get_queue", response_model=Queue)
def get_queue(name: str, redis: get_redis_connection = Depends()):
    """Returns stats for the specified queue
    """

    return RQInspector(redis).get_queue_stats(name)


@rq_jobs_v1_router.get("/queues/{name}/scheduled", name="rq_jobs_v1:get_queue_scheduled",
        response_model=Page[Job])
def get_queue_scheduled_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Returns the jobs that are scheduled to be added to the queue at the specified time
    """

    return  RQInspector(redis).get_scheduled_jobs(name, page, page_size)


@rq_jobs_v1_router.get("/queues/{name}/jobs/queued", name="rq_jobs_v1:get_queue_jobs_queued",
        response_model=Page[Job])
def get_queue_queued_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Gets the jobs that are queued in the given queue
    """

    return RQInspector(redis).get_queue_registry_jobs(
        name, "scheduled_job_registry", page, page_size
    )


@rq_jobs_v1_router.get("/queues/{name}/jobs/deferred", name="rq_jobs_v1:get_queue_jobs_deferred",
        response_model=Page[Job])
def get_queued_deferred_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Gets the jobs that are deferred in the given queue
    """

    return RQInspector(redis).get_queue_registry_jobs(
        name, "deferred_job_registry", page, page_size
    )


@rq_jobs_v1_router.get("/queues/{name}/jobs/started", name="rq_jobs_v1:get_queue_jobs_started",
        response_model=Page[Job])
def get_queued_started_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Gets the jobs that are started in the given queue
    """

    return RQInspector(redis).get_queue_registry_jobs(name, "started_job_registry", page, page_size)


@rq_jobs_v1_router.get("/queues/{name}/jobs/finished", name="rq_jobs_v1:get_queue_jobs_finished",
        response_model=Page[Job])
def get_queued_finished_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Gets the jobs that are finished in the given queue
    """

    return RQInspector(redis).get_queue_registry_jobs(
        name, "finished_job_registry", page, page_size
    )


@rq_jobs_v1_router.get("/queues/{name}/jobs/failed", name="rq_jobs_v1:get_queue_jobs_failed",
        response_model=Page[Job])
def get_queued_failed_jobs(name: str, page: int=1, page_size: int=8,
        redis: get_redis_connection = Depends()):
    """Gets the jobs that are failed in the given queue
    """

    return RQInspector(redis).get_queue_registry_jobs(name, "failed_job_registry", page, page_size)


#pylint: disable=redefined-builtin
@rq_jobs_v1_router.get("/queues/jobs/{id}", name="rq_jobs_v1:get_job", response_model=JobDetailed)
def get_job(id: str, redis: get_redis_connection = Depends()):
    """Returns details about the specified job
    """

    return RQInspector(redis).get_job(id, True)

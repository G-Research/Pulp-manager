"""RQ Job models
"""
# pylint: disable=no-name-in-module
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class Queue(BaseModel):
    """Schema object for a RQ Queue
    """

    name: str
    queued_jobs: int
    deferred_jobs: int
    started_jobs: int
    finished_jobs: int
    failed_jobs: int


class Job(BaseModel):
    """Schema object for a RQ Job
    """

    id: Optional[str]
    args: Optional[List]
    meta: dict
    status: Optional[str]
    enqueued_at: Optional[datetime]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    result_ttl: Optional[int]
    ttl: Optional[int]
    timeout: Optional[int]


class JobDetailed(Job):
    """Additional information when job quered by id
    """

    exc_info: Optional[str]

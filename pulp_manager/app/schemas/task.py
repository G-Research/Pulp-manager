"""Response models for tasks
"""

# pylint: disable=no-name-in-module
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TaskStage(BaseModel):
    """For a task that has mutiple steps to run to complete the task,
    the task stages when set given extra detail
    """

    id: int
    task_id: int
    name: str
    detail: Optional[dict]
    error: Optional[dict]

    class Config:
        """Internal class to state schema linked to ORM
        """

        orm_mode=True


class Task(BaseModel):
    """A Task is a background job, which pulp manager is to carry out.
    """

    id: int
    name: str
    parent_task_id: Optional[str]
    task_type: str
    task_args: Optional[dict]
    date_queued: datetime
    date_started: Optional[datetime]
    date_finished: Optional[datetime]
    state: str
    error: Optional[dict]
    worker_name: Optional[str]
    worker_job_id: Optional[str]

    class Config:
        """Internal class to state schema linked to ORM
        """

        orm_mode=True


class TaskDetail(Task):
    """TaskDetail includes all the same information as Task, with the additional
    of the TaskStages also being returned
    """

    stages: Optional[List[TaskStage]]


class TaskState(BaseModel):
    """Model for posting to change the state of a task
    """

    state: str

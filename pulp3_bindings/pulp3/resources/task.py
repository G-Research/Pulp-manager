"""implementation of the basic repository repo
"""

from datetime import datetime
from typing import List, Optional
from .base import Pulp3BaseModel


class ProgressReport(Pulp3BaseModel):
    """ProgressReport gives a status on the series of steps that are being carried out
    by a task
    """

    message: str
    code: str
    state:  str
    total: Optional[int]
    done: int
    suffix: Optional[str]


class Task(Pulp3BaseModel):
    """Task object contains the details about an asynchronous action that was
    carried out in pulp
    """

    pulp_href: str
    pulp_created: datetime
    state: str
    name: str
    logging_cid: str
    created_by: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[dict]
    worker: Optional[str]
    parent_task: Optional[str]
    child_tasks: Optional[List[str]]
    task_group: Optional[str]
    created_resources: Optional[List[Optional[str]]]
    reserved_resources_record: Optional[List[str]]

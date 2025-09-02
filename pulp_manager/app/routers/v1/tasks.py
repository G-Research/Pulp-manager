"""router for tasks route
"""
# pylint: disable=too-many-arguments,unused-argument,redefined-builtin,too-many-locals
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from pulp_manager.app.auth import JWTBearer
from pulp_manager.app.config import CONFIG
from pulp_manager.app.database import get_session
from pulp_manager.app.exceptions import (
    PulpManagerEntityNotFoundError, PulpManagerTaskInvalidStateError
)
from pulp_manager.app.models import TaskType, TaskState as TaskStateEnum
from pulp_manager.app.job_manager import JobManager
from pulp_manager.app.repositories import TaskRepository
from pulp_manager.app.route import LoggingRoute, parse_route_args
from pulp_manager.app.schemas import Page, Task, TaskDetail, TaskState


task_v1_router = APIRouter(
    prefix='/v1/tasks',
    tags=['tasks'],
    responses={404: {'description': 'Not Found'}},
    route_class=LoggingRoute
)


@task_v1_router.get("/", name="tasks_v1:all", response_model=Page[Task])
def get_all(name: Optional[str]=None, name__match: Optional[str]=None,
        parent_task_id: Optional[int]=None, state: Optional[str]=None,
        task_type: Optional[str] = None, worker_name: Optional[str]=None,
        worker_job_id: Optional[str] = None, date_queued__le: Optional[datetime]=None,
        date_queued__ge: Optional[datetime]=None, date_started__le: Optional[datetime]=None,
        date_started__ge: Optional[datetime]=None, date_finished__le: Optional[datetime]=None,
        date_finished__ge: Optional[datetime]=None, sort_by: Optional[str] = None,
        order_by: Optional[str] = None, page: int=1,
        page_size: int=CONFIG["paging"]["default_page_size"], db: get_session=Depends()):
    """Returns all tasks
    """

    query_params = parse_route_args(**locals())
    return TaskRepository(db).filter_paged_result(**query_params)


@task_v1_router.get("/task_types", name="tasks_v1:task_types", response_model=List[str])
def get_task_types():
    """Returns a list of task types that are supported
    """

    return [task_type.name for task_type in TaskType]


@task_v1_router.get("/task_states", name="tasks_v1:task_states", response_model=List[str])
def get_task_states():
    """Returns a list of task states that are supported
    """

    return [task_state.name for task_state in TaskStateEnum]


@task_v1_router.get("/{id}", name="tasks_v1:get_task", response_model=TaskDetail)
def get(id: int, db: get_session=Depends()):
    """Returns the specified task including stages
    """

    task = TaskRepository(db).get_by_id(id, eager=["stages"])
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@task_v1_router.patch(
    "/{id}", name="tasks_v1:change_state", response_model=Task,
    dependencies=[Depends(JWTBearer(allowed_groups=CONFIG["auth"]["admin_group"].split(",")))]
)
def change_state(id: int, task_state: TaskState, db: get_session=Depends()):
    """Changes the state of the task and also updates rq job if running. Currently
    only supports moving task to cancelled
    """

    try:
        return JobManager(db).change_task_state(id, task_state.state)
    except PulpManagerEntityNotFoundError as exception:
        raise HTTPException(status_code=404, detail="Task not found") from exception
    except PulpManagerTaskInvalidStateError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception

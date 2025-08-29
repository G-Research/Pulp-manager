"""Models for tasks
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    ForeignKey, Integer, String, DateTime, func, SmallInteger, Index
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.mysql import LONGTEXT
from pulp_manager.app.models.base import PulpManagerBaseId


class TaskType(Enum):
    """Task types supported by pulp manager for tagging and querying

    Task explanations:
    - repo_sync: when the task is synching an individual repo
    - repo_group_sync: when a group a repos are being synched, parent task
                       will be of type repo_group_sync, whilst the child job
                       where the individual repo is being synched will be of
                       type repo_sync
    """

    #pylint: disable=invalid-name
    repo_sync = 1
    repo_group_sync = 2
    repo_snapshot = 3
    repo_creation_from_git = 4
    repo_removal = 5
    remove_repo_content = 5


class TaskState(Enum):
    """States tasks can move through

    Status explanations:
    - queued: task is queued and waiting to start
    - running: task is running
    - completed: task completed successfully
    - failed: task failed/didn't complete successfully
    - canceled: task was canceled
    - failed_to_start: task failed to enter the running state
    - skipped: task was skipped
    """

    #pylint: disable=invalid-name
    queued = 1
    running = 2
    completed = 3
    failed = 4
    canceled = 5
    failed_to_start = 6
    skipped = 7


class TaskStage(PulpManagerBaseId):
    """Holds information about the stage of a task.

    :var task_id: ID of the tage the stage is linked to
    :var name: name of the stage
    :var detail_str: extra information about the task. This is a json string.
                     detail property attemps to do a json dump and load of the
                     field
    """

    __tablename__ = "task_stages"

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", name="task_stages__fk__task_id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    detail_str: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    error_str: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    task: Mapped["Task"] = relationship(back_populates="stages")

    @property
    def detail(self):
        """Returns the detail_str as a dict
        """

        if self.detail_str is not None:
            return json.loads(self.detail_str)
        return {}

    @detail.setter
    def detail(self, value: dict):
        """Taskes the dict value of the detail and then dumps it as a string in detail_str
        """

        self.detail_str = json.dumps(value)

    @property
    def error(self):
        """Returns the error_str as a dict
        """

        if self.error_str is not None:
            return json.loads(self.error_str)
        return {}

    @error.setter
    def error(self, value: dict):
        """Takes the dict value of the error and then dumps it as a string in error_str 
        """

        self.error_str = json.dumps(value)

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(id=self.id, name=self.name, task_id=self.task_id)

# pylint: disable=all
class Task(PulpManagerBaseId):
    """Holds information about tasks

    :var name: Name of the task
    """

    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tasks.id", name="tasks__fk__task_id", ondelete="CASCADE")
    )
    task_type_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    task_args_str: Mapped[Optional[str]] = mapped_column(LONGTEXT, nullable=False)
    #pylint: disable=not-callable
    date_queued: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    date_started: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    date_finished: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    worker_name: Mapped[Optional[str]] = mapped_column(String(256))
    worker_job_id: Mapped[Optional[str]] = mapped_column(String(256))
    error_str: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    parent_task: Mapped["Task"] = relationship(
        foreign_keys=[parent_task_id],
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan",
    )
    stages: Mapped[List["TaskStage"]] = relationship(
        back_populates="task",
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan"
    )
    pulp_server_repo_tasks: Mapped[List["PulpServerRepoTask"]] = relationship(
        back_populates="task",
        passive_deletes=True,
        cascade="save-update, merge, delete, delete-orphan",
    )

    __table_args__ = (
        Index("tasks__index__task_type_id", task_type_id),
        Index("tasks__index__date_queued", date_queued),
        Index("tasks__index__date_started", date_started),
        Index("tasks__index_date_finished", date_finished),
        Index("tasks__index__state_id", state_id),
        Index("tasks__index__worker_name", worker_name),
        Index("tasks__index_worker_job_id", worker_job_id)
    )

    @property
    def task_type(self):
        """Getter for converting take_type_id into string
        """

        if self.task_type_id is not None:
            return TaskType(self.task_type_id).name
        return None

    @task_type.setter
    def task_type(self, value):
        """Setter which takes a string and sets task_type_id, or accepts a valid enum ID directly.
        
        :param value: Name of the task type or its integer ID
        :type value: str or int
        """
        if isinstance(value, int):
            if value in TaskType._value2member_map_:
                self.task_type_id = value
            else:
                raise ValueError(f"Invalid task type ID: {value}")
        elif isinstance(value, str):
            try:
                self.task_type_id = TaskType[value.lower()].value
            except KeyError:
                raise ValueError(f"Invalid task type specified: {value}")
        else:
            raise TypeError(f"Expected string or integer for task type, got {type(value).__name__}")

    @property
    def state(self):
        """Getter for converting state_id into string
        """

        if self.state_id is not None:
            return TaskState(self.state_id).name
        return None

    @state.setter
    def state(self, value):
        """Setter which takes a string and sets state_id.
        
        :param value: Name of the state to set or its integer ID
        :type value: str or int
        """

        if isinstance(value, int):
            if value in TaskState._value2member_map_:
                self.state_id = value
            else:
                raise ValueError(f"Invalid task state ID: {value}")
        elif isinstance(value, str):
            try:
                self.state_id = TaskState[value.lower()].value
            except KeyError:
                raise ValueError(f"Invalid task state specified: {value}")
        else:
            raise TypeError(f"Expected string or integer for task state, "
                            f"got {type(value).__name__}")

    @property
    def task_args(self):
        """Returns the task_args_str as a dict
        """

        if self.task_args_str is not None:
            return json.loads(self.task_args_str)
        return {}

    @task_args.setter
    def task_args(self, value: dict):
        """Taskes the dict value of the task args and then dumps it as a string in task_args_str
        """

        self.task_args_str = json.dumps(value)

    def __repr__(self):
        """Override the SQLAlchemy representation of the entity
        """

        return self._repr(
            id=self.id, name=self.name, parent_task_id=self.parent_task_id, state=self.state
        )

    @property
    def error(self):
        """Returns the error_str as a dict
        """

        if self.error_str is not None:
            return json.loads(self.error_str)
        return {}

    @error.setter
    def error(self, value: dict):
        """Takes the dict value of the error and then dumps it as a string in error_str 
        """

        self.error_str = json.dumps(value)

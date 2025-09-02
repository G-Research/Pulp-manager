import logging
from datetime import datetime
from typing import Optional, Dict, TypedDict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pulp_manager.app.repositories import TaskRepository, TaskStageRepository
from pulp_manager.app.models import TaskState

class TaskInfo(TypedDict, total=False):
    """Typed dictionary to specify optional and required fields for task creation."""

    name: str
    task_args: Dict
    task_type: str
    worker_name: Optional[str]
    worker_job_id: Optional[int]


class TaskUpdateInfo(TypedDict, total=False):
    """Typed dictionary for specifying fields available for updating an existing task."""

    new_state: TaskState
    worker_name: Optional[str]
    worker_job_id: Optional[int]
    task_args: Dict


class TaskService:
    """
    A service class for managing tasks and task stages in the database.
    """
    def __init__(self, db_session: Session):
        """
        Initialize the TaskService with a database session.
        :param db_session: A SQLAlchemy Session instance used for database operations.
        """
        self.db_session = db_session
        self.task_crud = TaskRepository(db_session)
        self.task_stage_crud = TaskStageRepository(db_session)

    def _commit_to_db(self):
        """
        Commit the current transaction to the database and handle any exceptions.
        """
        try:
            self.db_session.commit()
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logging.error(
                "Database transaction failed and rolled back: %s", str(e), exc_info=True
            )
            raise

    def create_task(self, task_info: TaskInfo):
        """
        Create a new task and persist it to the database.
        :param task_info: TaskInfo dictionary containing task details.
        :return: The created task object.
        """
        try:
            task = self.task_crud.add(
                name=task_info["name"],
                task_args=task_info.get("task_args", {}),
                task_type=task_info["task_type"],
                state=TaskState.queued.value,
                worker_name=task_info.get("worker_name"),
                worker_job_id=task_info.get("worker_job_id"),
            )
            self._commit_to_db()
            return task
        except Exception as e:
            logging.error("Failed to create task: %s", str(e), exc_info=True)
            self.db_session.rollback()
            raise

    def update_task(self, task_id: int, task_updates: TaskUpdateInfo):
        """
        Update an existing task with new details.
        :param task_id: The ID of the task to update.
        :param task_updates: TaskUpdateInfo dictionary containing updates.
        :return: The updated task object or None if the task is not found.
        """
        task = self.task_crud.get_by_id(task_id)
        if not task:
            logging.warning(f"Task ID {task_id} not found.")
            return None

        try:
            update_data = {
                "state": task_updates["new_state"].value,
                "worker_name": task_updates.get("worker_name", task.worker_name),
                "worker_job_id": task_updates.get("worker_job_id", task.worker_job_id),
                "task_args": {**task.task_args, **task_updates.get("task_args", {})},
            }
            self.task_crud.update(task, **update_data)
            self._commit_to_db()
            return task
        except Exception as e:
            logging.error(
                "Failed to update task ID %d: %s", task_id, str(e), exc_info=True
            )
            self.db_session.rollback()
            raise

    def complete_task(self, task_id: int):
        """
        Mark a task as completed.
        :param task_id: The ID of the task to mark as complete.
        :return: The updated task object or None if the task is not found.
        """
        task = self.task_crud.get_by_id(task_id)
        if task:
            task.state = TaskState.completed.value
            task.date_finished = datetime.utcnow()
            try:
                self.task_crud.update(task)
                self._commit_to_db()
                logging.info(f"Task ID {task_id} marked as completed.")
                return task
            except Exception as e:
                logging.error(
                    f"Failed to complete task ID {task_id}: {str(e)}", exc_info=True
                )
                self.db_session.rollback()
                raise
        else:
            logging.warning(f"Task ID {task_id} not found.")
            return None

    def log_task_error(self, task_id: int, error_trace: str):
        """
        Log an error message to a task and change its state to ERROR.
        :param task_id: The ID of the task.
        :param error_trace: The error stack trace or message describing the error.
        """
        task = self.task_crud.get_by_id(task_id)
        if task:
            task.state = TaskState.failed.value
            task.error = {"message": error_trace}
            task.date_finished = datetime.utcnow()
            try:
                self.task_crud.update(task)
                self._commit_to_db()
                logging.error(f"Error logged for task ID {task_id}: {error_trace}")
            except Exception as e:
                logging.error(
                    f"Failed to log error for task ID {task_id}: {str(e)}",
                    exc_info=True,
                )
                self.db_session.rollback()
                raise
        else:
            logging.warning(f"Task ID {task_id} not found for error logging.")

    def add_task_stage(self, task_id: int, stage_name: str, detail: Dict):
        """
        Add a new stage to a specific task in the database.
        :param task_id: The ID of the task to which the stage is added.
        :param stage_name: Name of the task stage.
        :param detail: A dictionary containing detailed information about the task stage.
        :return: The created task stage object or None if the task does not exist.
        """
        # Check if the task exists before adding a stage
        task = self.task_crud.get_by_id(task_id)
        if not task:
            logging.warning(f"Task ID {task_id} not found.")
            return None

        try:
            task_stage = self.task_stage_crud.add(
                name=stage_name,
                task_id=task_id,
                detail=detail,
            )
            self._commit_to_db()
            logging.info(f"Task stage '{stage_name}' added to task ID {task_id}.")
            return task_stage
        except Exception as e:
            logging.error(
                f"Failed to add task stage to task ID {task_id}: {str(e)}",
                exc_info=True,
            )
            self.db_session.rollback()
            raise

    def update_task_stage(self, task_stage_id: int, message: str):
        """
        Update an existing task stage with new details.
        :param task_stage_id: The ID of the task stage to update.
        :param message: A message detailing the update to be logged and stored in the task stage.
        :return: The updated task stage object or None if the task stage is not found.
        """
        task_stage = self.task_stage_crud.get_by_id(task_stage_id)
        if not task_stage:
            logging.warning(f"Task stage ID {task_stage_id} not found.")
            return None

        try:
            self.task_stage_crud.update(task_stage, **{"detail": {"msg": message}})
            self._commit_to_db()
            logging.info(
                f"Task stage ID {task_stage_id} updated with message: {message}"
            )
            return task_stage
        except Exception as e:
            logging.error(
                f"Failed to update task stage ID {task_stage_id}: {str(e)}",
                exc_info=True,
            )
            self.db_session.rollback()
            raise

"""RepoRemover carries out the removal of repos based on regex patterns.
"""

import traceback
import socket
from typing import List
from datetime import datetime

from rq import get_current_job
from sqlalchemy.orm import Session


from pulp_manager.app.exceptions import (
    PulpManagerValueError,
    PulpManagerEntityNotFoundError,
)
from pulp_manager.app.models import TaskType, TaskState, PulpServerRepo
from pulp_manager.app.repositories import (
    PulpServerRepository,
    TaskRepository,
    PulpServerRepoTaskRepository,
    TaskStageRepository,
)
from pulp_manager.app.services.base import PulpServerService
from pulp_manager.app.services.reconciler import PulpReconciler
from pulp_manager.app.utils import log
from .pulp_helpers import get_pulp_server_repos, new_pulp_client, delete_by_href_monitor

# pylint: disable=too-many-instance-attributes, duplicate-code
class RepoRemover(PulpServerService):
    """
    The RepoRemover service is responsible for removing repositories from a Pulp server
    based on specified inclusion and exclusion regex patterns. This service allows for
    both actual removals and dry run operations where the removal actions are logged
    but not executed.

    It relies on direct interaction with the Pulp API through a Pulp client and uses
    the application's database models and services for task management and logging.

    Attributes:
        db (Session): The SQLAlchemy database session.
        pulp_server_name (str): The name of the Pulp server instance.
        _pulp_client: The Pulp client initialized for API interactions.
    """

    def __init__(self, db: Session, name: str):
        """Constructor
        :param db: DB session to use
        :type db: Session
        :param name: name of the pulp instance to interact with
        :type name: str
        """
        self._db = db
        self._pulp_server_crud = PulpServerRepository(db)
        self._task_crud = TaskRepository(db)
        self._task_stage_crud = TaskStageRepository(db)
        self._pulp_server_repo_task_crud = PulpServerRepoTaskRepository(db)
        self._reconciler = PulpReconciler(db, name)

        pulp_server_search = self._pulp_server_crud.get_pulp_server_with_repos(
            **{"name": name}
        )
        if len(pulp_server_search) == 0:
            raise PulpManagerEntityNotFoundError(
                f"Pulp server with name {name} not found"
            )

        self._pulp_server = pulp_server_search[0]
        self._pulp_client = new_pulp_client(self._pulp_server)
        self._task = None

        job = get_current_job()
        self._job_id = job.id if job else None

    def _get_repos_for_removal(
        self, regex_include: str, regex_exclude: str
    ) -> List[PulpServerRepo]:
        """Gets the list of repos for removal based on regex patterns.

        :param regex_include: regex pattern to include repos for removal
        :type regex_include: str
        :param regex_exclude: regex pattern to exclude repos from removal
        :type regex_exclude: str
        :return: A list of PulpServerRepo objects that match 
            the include pattern but not the exclude pattern
        :rtype: List[PulpServerRepo]
        """

        task_stage_name = (
            "Getting Repos for Removal (Dry Run)"
            if self._job_id
            else "Getting Repos for Removal"
        )
        task_stage = self._task_stage_crud.add(
            **{
                "name": task_stage_name,
                "task_id": self._task.id,
                "detail": {"msg": "Getting repos for removal based on regex patterns"},
            }
        )
        self._db.commit()

        matching_repos = get_pulp_server_repos(
            self._pulp_server, regex_include, regex_exclude, exclude_no_remote=False
        )

        if len(matching_repos) == 0:
            raise PulpManagerValueError(
                "No repositories found matching the regex pattern"
            )

        message = (
            f"Found matching repositories: {', '.join([repo.repo.name for repo in matching_repos])}"
        )
        log.info(message)

        self._task_stage_crud.update(
            task_stage, **{"detail": {"msg": message}})
        self._db.commit()

        return matching_repos

    def _remove_repos(
        self, repos_to_remove: List[PulpServerRepo], dry_run: bool = True
    ):
        """
        Manages the removal of repositories, distributions, and remotes from a Pulp server.

        This method performs the removal of specified repository objects. It can operate in a
        dry run mode where no actual deletions are performed, but the intended deletions are logged,
        or in a real mode where the items are actually deleted. The method handles logging of the
        operations, updates task stages, commits database transactions, and performs reconciliations
        post-deletion if not in dry run mode.

        Parameters:
            repos_to_remove (List[PulpServerRepo]): A list of PulpServerRepo objects that are to be
                removed. Each object should have attributes `repo_href`, `distribution_href`, and
                `remote_href` pointing to the respective items in the Pulp server.
            dry_run (bool): If True, the method will only simulate the removals without performing
                any actual changes. Defaults to True.

        Raises:
            ValueError: If the `_task` attribute is not set, indicating that the method was invoked
                without proper task setup.

        Returns:
            None: The method does not return any value but logs the results of the removal process
                or the simulated outcomes depending on the `dry_run` parameter.
        """

        if not repos_to_remove:
            log.info("No repositories specified for removal.")
            return

        if not self._task:
            raise ValueError(
                "Task is not initialized. Ensure that the task is set up "
                "correctly before fetching repos."
            )

        repo_hrefs = [repo.repo_href for repo in repos_to_remove]
        distribution_hrefs = [
            repo.distribution_href for repo in repos_to_remove if repo.distribution_href
        ]
        remote_hrefs = [
            repo.remote_href for repo in repos_to_remove if repo.remote_href
        ]

        stage_detail_msg = (
            "Preparing to remove {} repositories, distributions, and remotes."
        )
        task_stage_name = (
            "Removing Repositories and their Distributions/Remotes (Dry Run)"
            if dry_run
            else "Removing Repositories and their Distributions/Remotes"
        )
        task_stage = self._task_stage_crud.add(
            name=task_stage_name,
            task_id=self._task.id,
            detail={"msg": stage_detail_msg.format(len(repos_to_remove))},
        )
        self._db.commit()

        successful_deletions = 0
        failed_deletions = 0

        if dry_run:
            log.info(
                f"Dry run: Would remove distributions: {', '.join(distribution_hrefs)}, "
                f"repositories: {', '.join(repo_hrefs)}, remotes: {', '.join(remote_hrefs)}"
            )
            successful_deletions = len(repos_to_remove)
        else:
            for repo in repos_to_remove:
                try:
                    if repo.distribution_href:
                        # Remove the distribution.
                        delete_by_href_monitor(
                            self._pulp_client,
                            repo.distribution_href,
                            poll_interval_sec=2,
                            max_wait_count=200,
                        )
                    # Remove the repository.
                    delete_by_href_monitor(
                        self._pulp_client,
                        repo.repo_href,
                        poll_interval_sec=2,
                        max_wait_count=200,
                    )
                    # Remove the remote.
                    if repo.remote_href:
                        delete_by_href_monitor(
                            self._pulp_client,
                            repo.remote_href,
                            poll_interval_sec=2,
                            max_wait_count=200,
                        )

                    log.info(f"Successfully removed distribution, repository, "
                            f"and remote for {repo.repo.name}")
                    successful_deletions += 1
                except Exception as e:
                    log.error(
                        f"Error during removal for {repo.repo.name}: {e}")
                    failed_deletions += 1

        completion_msg = (
            f"Completed removing repositories, distributions, and remotes. "
            f"Successfully removed {successful_deletions}, failed to remove {failed_deletions}"
        )
        completion_msg += " (Dry Run)" if dry_run else ""
        log.info(completion_msg)
        self._task_stage_crud.update(
            task_stage, detail={"msg": completion_msg})
        self._db.commit()

        if not dry_run and successful_deletions > 0:
            self._reconciler.reconcile()
            log.info("Reconciliation completed after removals.")

    def remove_repos(
        self,
        regex_include: str = None,
        regex_exclude: str = None,
        dry_run: bool = True,
        task_id: int = None,
    ) -> None:
        """Public method to initiate repo removal based on provided patterns."""
        log.info(f"{'Dry run: ' if dry_run else ''}Starting removal of repositories...")

        if regex_include is None and regex_exclude is None:
            log.error(
                "Invalid parameters: regex_include and regex_exclude cannot both be None"
            )
            raise ValueError(
                "Must specify at least one of regex_include or regex_exclude"
            )

        if task_id is None:
            self._task = self._task_crud.add(
                **{
                    "name": f"{self._pulp_server.name} repo removal",
                    "task_type_id": TaskType.repo_removal.value,
                    "state_id": TaskState.running.value,
                    "worker_name": socket.gethostname(),
                    "worker_job_id": self._job_id,
                    "task_args": {
                        "regex_include": regex_include,
                        "regex_exclude": regex_exclude,
                        "dry_run": dry_run,
                    },
                }
            )
            self._db.commit()
        else:
            self._task = self._task_crud.get_by_id(task_id)
            if self._task is None:
                message = f"Task with ID {task_id} not found"
                log.error(message)
                raise PulpManagerValueError(message)

            self._task_crud.update(
                self._task,
                **{
                    "state_id": TaskState.running.value,
                    "worker_job_id": self._job_id,
                    "worker_name": socket.gethostname(),
                },
            )
            self._db.commit()

        try:
            repos_to_remove = self._get_repos_for_removal(regex_include, regex_exclude)
            self._remove_repos(repos_to_remove, dry_run)
            if self._task:
                self._task_crud.update(
                    self._task,
                    **{
                        "state_id": TaskState.completed.value,
                        "date_finished": datetime.utcnow(),
                    }
                )
                self._db.commit()
        except Exception as e:
            log.error(f"An error occurred during repository removal: {e}")
            log.error(traceback.format_exc())
            if self._task:
                self._task_crud.update(
                    self._task,
                    **{
                        "state": TaskState.failed.value,
                        "date_finished": datetime.utcnow(),
                        "error": {
                            "msg": "Failed to remove repositories",
                            "detail": traceback.format_exc(),
                        },
                    },
                )
            raise

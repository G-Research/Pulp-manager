"""Snapshotter carries out the snapshotting of repos, it doesn't
do repo registration on slaves
"""
import re
import socket
import traceback
from datetime import datetime
from time import sleep
from typing import List

from rq import get_current_job
from sqlalchemy.orm import Session

from pulp3_bindings.pulp3.remotes import get_remote
from pulp3_bindings.pulp3.repositories import get_repo, get_all_repos, copy_repo
from pulp3_bindings.pulp3.tasks import get_task

from pulp_manager.app.exceptions import (
    PulpManagerValueError, PulpManagerSnapshotError, PulpManagerEntityNotFoundError
)
from pulp_manager.app.models import TaskType, TaskState, PulpServerRepo, Task
from pulp_manager.app.repositories import (
    PulpServerRepository, RepoRepository, PulpServerRepoRepository, TaskRepository,
    PulpServerRepoTaskRepository, TaskStageRepository
)
from pulp_manager.app.services.base import PulpServerService
from pulp_manager.app.services.reconciler import PulpReconciler
from pulp_manager.app.services.pulp_manager import PulpManager
from pulp_manager.app.utils import log
from .pulp_helpers import get_pulp_server_repos, new_pulp_client, get_repo_type_from_href


SNAPSHOT_STAGE_NAME = "repo snapshot"
PUBLISH_STAGE_NAME = "repo publication"
SUPPORTED_FOR_SNAPSHOT = ["rpm", "deb"]


#pylint: disable=too-many-instance-attributes
class Snapshotter(PulpServerService):
    """Carries out snapshotting of repos, doesn't do registering on slsaves
    """

    def __init__(self, db: Session, name: str):
        """Constructor
        :param db: DB session to use
        :type db: Session
        :param name: name of the pulp instance to carry out interaction on
        :type name: str
        """

        self._db = db
        self._pulp_server_crud = PulpServerRepository(db)
        self._repo_crud = RepoRepository(db)
        self._pulp_server_repo_crud = PulpServerRepoRepository(db)
        self._task_crud = TaskRepository(db)
        self._task_stage_crud = TaskStageRepository(db)
        self._pulp_server_repo_task_crud = PulpServerRepoTaskRepository(db)
        self._pulp_manager = PulpManager(db, name)

        #pylint: disable=duplicate-code
        pulp_server_search = self._pulp_server_crud.get_pulp_server_with_repos(**{"name": name})

        if len(pulp_server_search) == 0:
            raise PulpManagerEntityNotFoundError(f"pulp server with name {name} not found")

        self._pulp_server = pulp_server_search[0]
        self._pulp_client = new_pulp_client(self._pulp_server)
        self._task = None

        job = get_current_job()
        self._job_id = job.id if job else None

    def get_supported_snapshot_repo_type(self):
        """Returns a list of repo types that are supported for snapshooting

        :return: List[str]
        """

        return SUPPORTED_FOR_SNAPSHOT

    def _do_reconcile(self):
        """Carries out a reconcile of repos on the pulp server, to make sure
        all available for snapshotting
        """

        task_stage = self._task_stage_crud.add(**{
            "name": "reconcile repos",
            "detail": {"msg": "reconciling repos on pulp server"},
            "task_id": self._task.id
        })

        self._db.commit()

        try:
            pulp_reconciler = PulpReconciler(self._db, self._pulp_server.name)
            # DB refresh inside the reconile method will ensure that the
            # self._pulp_server has any new repo updates
            pulp_reconciler.reconcile()
            self._task_stage_crud.update(task_stage, **{
                "detail": {"msg": "completed repo reconcile"}
            })
            self._db.commit()
        except Exception:
            self._task_stage_crud.update(task_stage, **{
                "error": {
                    "msg": "failed to reconcile repos on pulp server",
                    "detail": traceback.format_exc()
                }
            })
            self._db.commit()
            raise

    def _get_repos_for_snapshot(self, regex_include: str, regex_exclude: str):
        """Gets the list of repos for snapshotting

        :param regex_include: regex of repos to be included in the snapshot
        :type regex_include: str
        :param regex_exclude: regex of repos to be excluded from the snapshot. If there are
                              repos that match regex_exclude and regex_include, then regex_exclude
                              takes precendence and the repo is excluded from the result
        :type regex_exclude: str
        :return List[PulpServerRepo]
        """

        task_stage = self._task_stage_crud.add(**{
            "name": "find repos to snapshot",
            "task_id": self._task.id,
            "detail": {"msg": "getting repos to snapshot"}
        })
        self._db.commit()

        matching_repos = get_pulp_server_repos(self._pulp_server, regex_include, regex_exclude)
        repos_to_snapshot = []
        repos_excluded = []

        for repo in matching_repos:
            if repo.repo.repo_type not in SUPPORTED_FOR_SNAPSHOT:
                repos_excluded.append(f"repo.repo.name {repo.repo.repo_type}")
            else:
                repos_to_snapshot.append(repo)

        message = f"there are {len(repos_to_snapshot)} repos to snapshot. "
        if len(repos_excluded) > 0:
            message += "The following repos will be excluded as not of a supported type: "
            message += f"{', '.join(repos_excluded)}"

        log.info(message)

        self._task_stage_crud.update(task_stage, **{"detail": {"msg": message}})

        return repos_to_snapshot

    def _start_snapshot(self, repo: PulpServerRepo, repo_snapshot_name: str):
        """Starts the snapshot of a repo and returns a task object which contains a stage
        that has the href to the running task for the snapshot

        :param repo: Pulp Server repo to snapshot
        :type repo: PulpServerRepo
        :param snapshot_name: The name of the snapshot repo where the repo contents is to be copied
                              into
        :type snapshot_name: str
        :return: Task
        """

        # Stages
        # 1. Ensure repo exists on pulp server
        # 2. Check if snapshot repo already exists
        # a. If repo doesn't exist create it
        # 3. Check is distribution exists
        # a. If distribution doesn't exist create it and link repo to it
        # 4. Start repo copy
        repo_snapshot_task = self._task_crud.add(**{
            "name": f"snapshot {repo.repo.name}",
            "date_started": datetime.utcnow(),
            "task_type_id": TaskType.repo_snapshot.value,
            "state_id": TaskState.running.value,
            "worker_name": socket.gethostname(),
            "worker_job_id": self._job_id,
            "task_args": {
                "source_repo_href": repo.repo_href,
            }
        })
        self._db.commit()

        try:
            pulp_source_repo = get_repo(self._pulp_client, repo.repo_href)
            repo_type = get_repo_type_from_href(repo.repo_href)

            pm_snapshot_pulp_server_repo = self._pulp_manager.create_or_update_repository(
                name=repo_snapshot_name,
                description=pulp_source_repo.description,
                repo_type=repo_type
            )

            pulp_snapshot_repo_search = get_all_repos(
                self._pulp_client, repo_type, params={"name": repo_snapshot_name}
            )
            pulp_snapshot_repo = pulp_snapshot_repo_search[0]

            pulp_task = copy_repo(self._pulp_client, pulp_source_repo, pulp_snapshot_repo)
            task_args = repo_snapshot_task.task_args
            task_args["dest_repo_href"] = pulp_snapshot_repo.pulp_href
            task_args["repo_type"] = repo_type
            self._task_crud.update(repo_snapshot_task, **{"task_args": task_args})
            self._db.commit()
            # Link the source repo and and snapshot repo to this task in the pulp manager db
            self._pulp_server_repo_task_crud.bulk_add([
                {
                    "pulp_server_repo_id": repo.id,
                    "task_id": repo_snapshot_task.id
                },
                {
                    "pulp_server_repo_id": pm_snapshot_pulp_server_repo.id,
                    "task_id": repo_snapshot_task.id
                },
            ])
            self._db.commit()

            # Create a task stage for the repo snapshot
            self._task_stage_crud.add(**{
                "name": SNAPSHOT_STAGE_NAME,
                "detail": {
                    "msg": f"task in state {pulp_task.state}",
                    "task_href": pulp_task.pulp_href
                },
                "task_id": repo_snapshot_task.id
            })
            self._db.commit()
        except Exception:
            message = f"error occured snapshotting {repo.repo.name}"
            log.error(message)
            log.error(traceback.format_exc())

            self._task_crud.update(
                repo_snapshot_task, **{
                    "date_finished": datetime.utcnow(),
                    "state_id": TaskState.failed.value,
                    "error": {
                        "msg": message,
                        "detail": traceback.format_exc()
                    }
                }
            )
            self._db.commit()

        return repo_snapshot_task

    def _start_publication(self, task: Task):
        """Starts the publication of the request repo. A new stage is added to the provided task

        :param task: Task entity to add a new stage to
        :type task: Task
        """

        pulp_repo = get_repo(self._pulp_client, task.task_args["dest_repo_href"])
        repo_type = get_repo_type_from_href(task.task_args["dest_repo_href"])

        is_flat_repo = False

        if repo_type == "deb":
            # The source repo will contain the remoite if one was configured so
            # need to grab this to check if the repo is flat and needs different
            # publication options
            source_pulp_repo = get_repo(self._pulp_client, task.task_args["source_repo_href"])
            if source_pulp_repo.remote:
                source_pulp_remote = get_remote(self._pulp_client, source_pulp_repo.remote)
                is_flat_repo = source_pulp_remote.is_flat_repo

        publication_task = self._pulp_manager.create_publication_from_repo_version(
            pulp_repo.latest_version_href, repo_type, is_flat_repo
        )

        #pylint: disable=duplicate-code
        self._task_stage_crud.add(**{
            "name": PUBLISH_STAGE_NAME,
            "task_id": task.id,
            "detail": {
                "msg": f"task in state {publication_task.state}",
                "task_href": publication_task.pulp_href
            }
        })
        self._db.commit()

    def _progress_snapshot(self, task: Task):
        """Checks the task being run by the current stage, and sees if it has finished.
        If the current stage has finished and there are more stage to be run then the next
        stage is started. If all stages have completed, or a stage has failed True is returned
        to indicated that the task has completed. False is returned when the task has not been
        completed, indicating that _progress_snapshot needs to be called again in the future.

        :param task: pulp manager task to check the status of
        :type task: Task
        :return: bool
        """

        current_stage = task.stages[-1]
        try:
            pulp_task = get_task(self._pulp_client, current_stage.detail["task_href"])
            if pulp_task.state not in ["running", "waiting"]:
                message = f"{current_stage.name} {pulp_task.state}. "
                detail = dict(current_stage.detail)
                detail["msg"] = message
                self._task_stage_crud.update(current_stage, **{"detail": detail})
                self._db.commit()

				#pylint: disable=no-else-return
                if pulp_task.state != "completed" or current_stage.name == PUBLISH_STAGE_NAME:
                    state = "failed" if pulp_task.state != "completed" else "completed"
                    self._task_crud.update(
        	            task, **{"state": state, "date_finished": datetime.utcnow()}
	                )
                    self._db.commit()
                    return True

                if current_stage.name == SNAPSHOT_STAGE_NAME:
                    self._start_publication(task)
            self._task_crud.update(task, **{"last_updated": datetime.utcnow()})
            return False

        except Exception:
            log.error(f"unexpected error occured progressing the snapshot for {task.id}")
            log.error(traceback.format_exc())
            self._db.commit()
            self._task_crud.update(
 	            task, **{
                    "state": "failed",
                    "date_finished": datetime.utcnow(),
                    "error": {
                        "msg": "unexpected error occured progressing the snapshot",
                        "detail": traceback.format_exc()
                    }
                }
	        )
            self._db.commit()
            raise
        return True

    #pylint: disable=too-many-locals
    def _do_snapshot_repos(self, snapshot_prefix: str, repos_to_snapshot: List[PulpServerRepo]):
        """Carries out the work of snapshotting and monitoring the repos

        :param snapshot_prefix: prefix to use for snapshots
        :type snapshot_prefix: str
        :param repos_to_snapshot: List of repos that should be snapshotted
        :type repos_to_snapshot: List[PulpServerRepo]
        """

        repos_left_to_snapshot = list(repos_to_snapshot)
        snapshots_in_progress = {}
        snapshots_failed = []

        snapshot_stage = self._task_stage_crud.add(**{
            "name": "snapshot repos",
            "task_id": self._task.id,
            "detail": {"msg": f"0/{len(repos_to_snapshot)} snapshots completed"}
        })
        self._db.commit()

        while len(repos_left_to_snapshot) != 0 or len(snapshots_in_progress) != 0:
            while (len(snapshots_in_progress) < self._pulp_server.max_concurrent_snapshots
                    and len(repos_left_to_snapshot) != 0):
                repo_to_snapshot = repos_left_to_snapshot.pop(0)
                repo_snapshot_name = f"{snapshot_prefix}{repo_to_snapshot.repo.name}"
                try:
                    snapshot_task = self._start_snapshot(repo_to_snapshot, repo_snapshot_name)
                    if snapshot_task.state_id != TaskState.running.value:
                        snapshots_failed.append(repo_to_snapshot)
                    else:
                        snapshots_in_progress[snapshot_task.id] = snapshot_task
                except Exception:
                    log.error(
                        f"Unexpected error in starting snapshot for {repo_to_snapshot.repo.name}"
                    )
                    log.error(traceback.format_exc())
                    snapshots_failed.append(repo_to_snapshot)

            snapshots_in_progress_copy = snapshots_in_progress.copy()

            for snapshot_task in snapshots_in_progress_copy.values():
                self._db.refresh(snapshot_task)

                try:
                    if self._progress_snapshot(snapshot_task):
                        del snapshots_in_progress[snapshot_task.id]
                except Exception:
                    log.error(f"_progress_snapshot failed for {snapshot_task.id}")
                    log.error(traceback.format_exc())
                    del snapshots_in_progress[snapshot_task.id]

            detail = snapshot_stage.detail
            num_snapshots_completed = (
                len(repos_to_snapshot) - len(repos_left_to_snapshot) - len(snapshots_in_progress)
            )
            detail["msg"] = (
                f"{num_snapshots_completed}/{len(repos_to_snapshot)} snapshots completed"
            )
            self._task_stage_crud.update(snapshot_stage, **{"detail": detail})
            self._db.commit()
            sleep(10)

        state = "failed" if len(snapshots_failed) > 0 else "completed"
        error_msg = ""
        if len(snapshots_failed) > 0:
            error_msg = f"the following repos failed {','}.join(snapshots_failed)"

        self._task_crud.update(
            self._task, **{
                "state": state,
                "date_finished": datetime.utcnow(),
                "error": {"msg": error_msg}
            }
        )
        self._db.commit()

    def _snapshot_allowed(self, snapshot_prefix: str):
        """Checks if an existing snapshot exists with the given prefix and if so errors
        """

        # Should probably just query the DB but this loop check should be quite in expensive
        for repo in self._pulp_server.repos:
            if re.match(f"^{snapshot_prefix}", repo.repo.name):
                raise PulpManagerSnapshotError(
                    f"snapshots with prefix {snapshot_prefix} already exist"
                )

    def snapshot_repos(self, snapshot_prefix: str, regex_include: str=None,
            regex_exclude: str= None, task_id: int=None,
            allow_snapshot_reuse: bool=False):
        """Carries out the snapshotting of repos on the specified pulp server

        :param snapshot_prefix: Prefix to use for snapshots
        :type snapshot_prefix: str
        :param regex_include: regex of repos to include in the snapshot
        :type regex_include: str
        :param regex_exclude: regex of repos to exclude from the snapshot. If repos match both
                              regex_include and regex_exclude, then regex_exclude takes precendence
                              and the repo is ignored
        :type regex_exclude: str
        :param task_id: Task the snapshot job is linked to. If set to none a new task will
                        be created
        :type task_id: None
        :param allow_snapshot_reuse: Identifies snapshots can be updated if they already exist.
                                     Defaults to False
        :type allow_snapshot_reuse: bool
        """

        log.info(
            f"Starting snapshot for {self._pulp_server.name}, snapshot_prefix: {snapshot_prefix}, "
            f"max_concurrent_snapshots: {self._pulp_server.max_concurrent_snapshots}, "
            f"regex_include {regex_include}, regex_exclude {regex_exclude}, task_id: {task_id}, "
            f"allow_snapshot_reuse: {allow_snapshot_reuse}"
        )

        if not snapshot_prefix.endswith("-"):
            snapshot_prefix += "-"
            log.info(f"snapshot prefix update to {snapshot_prefix}")

        if task_id is None:
            self._task = self._task_crud.add(**{
                "name": f"{self._pulp_server.name} repo snapshot",
                "task_type_id": TaskType.repo_snapshot.value,
                "state_id": TaskState.running.value,
                "date_started": datetime.utcnow(),
                "worker_name": socket.gethostname(),
                "worker_job_id": self._job_id,
                "task_args": {
                    "snapshot_prefix": snapshot_prefix,
                    "max_concurrent_snapshots": self._pulp_server.max_concurrent_snapshots,
                    "regex_include": regex_include,
                    "regex_exclude": regex_exclude,
                    "allow_snapshot_reuse": allow_snapshot_reuse
                }
            })
            self._db.commit()
        else:
            self._task = self._task_crud.get_by_id(task_id)
            if self._task is None:
                message = f"task with ID {task_id} not found"
                log.error(message)
                raise PulpManagerValueError(message)
            self._task_crud.update(self._task, **{
                "state_id": TaskState.running.value,
                "date_started": datetime.utcnow(),
                "worker_job_id": self._job_id,
                "worker_name": socket.gethostname()
            })
            self._db.commit()

        if not self._pulp_server.snapshot_supported:
            message = f"pulp server {self._pulp_server.name} not supported for repo snapshots"
            log.error(message)
            raise PulpManagerValueError(message)

        try:
            self._do_reconcile()

            if not allow_snapshot_reuse:
                self._snapshot_allowed(snapshot_prefix)

            repos_to_snapshot = self._get_repos_for_snapshot(regex_include, regex_exclude)
            self._do_snapshot_repos(snapshot_prefix, repos_to_snapshot)

        except Exception:
            self._task_crud.update(self._task, **{
                "state": "failed",
                "date_finished": datetime.utcnow(),
                "error": {
                    "msg": "failed to snapshot repos",
                    "detail": traceback.format_exc()
                }
            })
            self._db.commit()
            raise

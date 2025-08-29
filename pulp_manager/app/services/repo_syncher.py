"""Service that carrys out the synchronisation of repos
"""
#pylint: disable=too-many-lines
import logging
import json
import re
import socket
import traceback
from datetime import datetime
from time import sleep
from typing import List, Dict
from rq import get_current_job
from sqlalchemy.orm import Session

from pulp3_bindings.pulp3.resources import Repository
from pulp3_bindings.pulp3.publications import get_all_publications
from pulp3_bindings.pulp3.remotes import get_remote
from pulp3_bindings.pulp3.repositories import get_repo, sync_repo, get_repo_version, modify_repo
from pulp3_bindings.pulp3.tasks import get_task

from pulp_manager.app.config import CONFIG
from pulp_manager.app.exceptions import (
    PulpManagerEntityNotFoundError, PulpManagerTaskNotFoundError
)
from pulp_manager.app.models import PulpServerRepo, Task, TaskStage, TaskType, TaskState
from pulp_manager.app.services.base import PulpServerService
from pulp_manager.app.services.reconciler import PulpReconciler
from pulp_manager.app.services.pulp_manager import PulpManager
from pulp_manager.app.repositories import (
    TaskRepository, TaskStageRepository, PulpServerRepoTaskRepository, PulpServerRepository,
    PulpServerRepoRepository
)
from pulp_manager.app.utils import log
from .pulp_helpers import get_pulp_server_repos, new_pulp_client, get_repo_type_from_href


# Consts to stage names
SYNC_STAGE_NAME = "sync repo"
REMOVE_BANNED_PACKAGES_STAGE_NAME = "remove banned packages"
PUBLISH_STAGE_NAME = "publish repo"
SYNC_STAGE_ORDER = [SYNC_STAGE_NAME, REMOVE_BANNED_PACKAGES_STAGE_NAME, PUBLISH_STAGE_NAME]


class RepoSyncher(PulpServerService):
    """Carries out the synchronisation of indivual repos and groups of repos
    """

    #pylint: disable=too-many-instance-attributes
    def __init__(self, db: Session, name: str):
        """Constructor
        :param db: DB session to use
        :type db: Session
        :param name: name of the pulp instance to carry out interaction on
        :type name: str
        """

        self._db = db
        self._task_crud = TaskRepository(db)
        self._task_stage_crud = TaskStageRepository(db)
        self._pulp_server_crud = PulpServerRepository(db)
        self._pulp_server_repo_task_crud = PulpServerRepoTaskRepository(db)

        job = get_current_job()
        self._job_id = job.id if job else None

        #pylint: disable=duplicate-code
        pulp_server_search = self._pulp_server_crud.get_pulp_server_with_repos(**{"name": name})

        if len(pulp_server_search) == 0:
            raise PulpManagerEntityNotFoundError(f"pulp server with name {name} not found")

        self._pulp_server = pulp_server_search[0]
        self._pulp_client = new_pulp_client(self._pulp_server)

    def _get_repos_to_sync(self, regex_include: str=None, regex_exclude: str=None):
        """Return a list of pulp server repos that need to be synched
        :param regex_include: regex of repos to be included in the repo sync
        :type regex_include: str
        :param regex_exclude: regex of repos to exlude from the repo sync. If there are repos
                              that match both regex_exclude and regex_include, then regex_exclude
                              takes precendence and the repo is excluded from the sync
        :type regex_exclude: str
        :return: List[PulpServerRepo]
        """

        repos_to_sync = get_pulp_server_repos(self._pulp_server, regex_include, regex_exclude)

        log.info(f"There are {len(repos_to_sync)} repos to sync")
        if log.level == logging.DEBUG:
            repo_names = [repo.repo.name for repo in repos_to_sync]
            log.debug(f"The following repos will be synched {', '.join(repo_names)}")
        return repos_to_sync

    def _generate_tasks(self, pulp_server_name: str, repos: List[PulpServerRepo],
            parent_task_id: int):
        """Given the list of repos that will be synched, task entries are created in the DB
        and the list of Task entities is returned

        :param pulp_server_name: Name of the pulp server tasks are being generated for
        :type pulp_server_name: str
        :param repos; List of PulpServerRepos to have task objects created
        :type repos: List[PulpServerRepo]
        :param parent_task_id: Parent id the task is linked to
        :type parent_task_id: int
        :return: List[Task]
        """

        try:
            log.info(f"Staging the tasks for {len(repos)} repo syncs")
            tasks_to_create = []
            for pulp_repo in repos:
                tasks_to_create.append({
                    "name": f"{pulp_server_name} repo sync {pulp_repo.repo.name}",
                    "parent_task_id": parent_task_id,
                    "task_type_id": TaskType.repo_sync.value,
                    "state_id": TaskState.queued.value,
                    "worker_name": socket.gethostname(),
                    "worker_job_id": self._job_id,
                    "task_args_str": json.dumps({
                        "pulp_server_repo_id": pulp_repo.id,
                        "repo_href": pulp_repo.repo_href
                    })
                })

            tasks = self._task_crud.bulk_add(tasks_to_create)
            self._db.flush()
            log.info("Associating tasks with the pulp repos they are being synched with")

            repo_tasks_to_create = []
            for task in tasks:
                repo_tasks_to_create.append({
                    "pulp_server_repo_id": task.task_args["pulp_server_repo_id"],
                    "task_id": task.id
                })

            self._pulp_server_repo_task_crud.bulk_add(repo_tasks_to_create)
            self._db.commit()
            return tasks
        except Exception:
            log.error("generation of repo sync tasks failed for parent task {parent_task_id}")
            log.error(traceback.format_exc())
            raise

    def _start_sync(self, task: Task, sync_options: Dict):
        """Initites the repo sync and returns the task stage

        :param task: task the sync stage is to be linked to
        :type task: Task
        :param sync_options: Additional sync options to be set. These are repo type specific and
                             need to be looked up via the pulp API to see what is valid the group
                             of repos being synced
        :type sync_options: dict
        :return: TaskStage
        """

        task_stage = None
        try:
            task_stage = self._task_stage_crud.add(**{
                "name": SYNC_STAGE_NAME, "task_id": task.id
            })
            pulp_repo = get_repo(self._pulp_client, task.task_args["repo_href"])
            pulp_sync_task = sync_repo(
                self._pulp_client, pulp_repo,
                sync_options if sync_options else {}
            )
            self._db.commit()
            self._task_stage_crud.update(
                task_stage, **{
                    "detail": {
                        "msg": f"{SYNC_STAGE_NAME} in state {pulp_sync_task.state}",
                        "task_href": pulp_sync_task.pulp_href
                    }
                }
            )
            self._task_crud.update(
                task, **{
                    "state": "running",
                    "date_started": datetime.utcnow()
                }
            )
            self._db.commit()
            return task_stage
        except Exception:
            message = (f"unexpected error occured starting repo sync  "
                        f"for repo {task.task_args['repo_href']}")
            log.error(message)
            log.error(traceback.format_exc())
            if task_stage is not None:
                self._task_stage_crud.update(
                    task_stage, **{
                        "error": {
                            "msg": message,
                            "detail": traceback.format_exc()
                        }
                    }
                )
                self._task_crud.update(
                    task, **{
                        "state": "failed_to_start",
                        "date_finished": datetime.utcnow(),
                        "error": {
                            "msg": message,
                            "detail": traceback.format_exc()
                        }
                    }
                )
                self._db.commit()
            raise

    def _find_packages_to_remove(self, repo: Repository):
        """Checks for any packages that exist in the repo that should be removed.
        Returns a list of hrefs, which are for packages that should be removed
        by creating a new repo version

        :param repo: Repository to check the contents of
        :type repo: repository
        :return: list
        """

        log.debug(f"getting latest repo version for {repo.name}")
        latest_repo_version = get_repo_version(self._pulp_client, repo.latest_version_href)
        # latest package counts are stored in a content summary dict which will have
        # a key the format <package_type>.package e.g. rpm.package. So check this exists
        # and then can follow a link to all the packages that make up the repo
        match = re.match('/pulp/api/v3/repositories/([a-z]+)/', repo.pulp_href)
        package_type = match.groups()[0]
        package_key = f"{package_type}.package"
        packages_to_remove = []
        if ("present" in latest_repo_version.content_summary and
                package_key in latest_repo_version.content_summary["present"]):
            content_url = latest_repo_version.content_summary["present"][package_key]["href"]
            # Because there are os many results we just call get_page_results of the pulp client
            # directly, which will give us a list of dicts to work with
            # Due ot how the binding library builds URLs, we need to setup the parameter
            # repository_version ourselves
            content_href = content_url.split("?")[0]

            # debs have more efficient way to grab results. Sadly not all repo types support
            # grabbing by regex. This is to be reworked when looking to support python
            # and containers properly in pulp,as we may need to split each of these out
            # into their own function.
            if "/deb/" in repo.pulp_href:
                results = self._pulp_client.get_page_results(
                    content_href,
                    params={
                        "repository_version": repo.latest_version_href,
                        "package__iregex": CONFIG["pulp"]["banned_package_regex"]
                    }
                )
                packages_to_remove = [package["pulp_href"] for package in results]
            else:
                results = self._pulp_client.get_page_results(
                    content_href, params={"repository_version": repo.latest_version_href}
                )

                for package in results:
                    if re.search(CONFIG["pulp"]["banned_package_regex"], package["name"]):
                        log.debug(f"package {package['name']} matches "
                                f"{CONFIG['pulp']['banned_package_regex']}"
                        )
                        packages_to_remove.append(package["pulp_href"])

        log.debug(f"{len(packages_to_remove)} to remove from {repo.name}")
        return packages_to_remove

    def _start_remove_banned_packages(self, task: Task):
        """Checks if there are packages that need to be removed fro mthe repo
        and if so kicks off a task to do this. Returns True if a task was started,
        False is returned to indicate it was skipped. Packages only need banning
        when the feed is from an external URL.
        """

        pulp_repo = None
        task_stage = None
        log.debug(
            "checking if packages need to be removed from repo with href "
            f"{task.task_args['repo_href']}"
        )
        try:
            pulp_repo = get_repo(self._pulp_client, task.task_args["repo_href"])
            log.debug(f"repo with href {task.task_args['repo_href']} is called {pulp_repo.name}")
            pulp_remote = get_remote(self._pulp_client, pulp_repo.remote)
            log.debug(f"found remote for {pulp_repo.name}, {pulp_remote.pulp_href}")

            for internal_domain in CONFIG["pulp"]["internal_domains"].split(","):
                if internal_domain in pulp_remote.url:
                    message = f"stage skipped for {pulp_repo.name} as url is in internal domain"
                    log.debug(message)
                    task_stage = self._task_stage_crud.add(**{
                        "name": REMOVE_BANNED_PACKAGES_STAGE_NAME,
                        "task_id": task.id,
                        "detail": {"msg": message}
                    })
                    self._db.commit()
                    return False

            task_stage = self._task_stage_crud.add(**{
                "name": REMOVE_BANNED_PACKAGES_STAGE_NAME,
                "task_id": task.id,
                "detail": {"msg": "check if any banned packages need to be removed"}
            })
            self._db.commit()

            packages_to_remove = self._find_packages_to_remove(pulp_repo)
            if len(packages_to_remove) == 0:
                self._task_stage_crud.update(
                    task_stage, **{"detail": {"msg": "stage skipped no packages to remove"}}
                )
                self._db.commit()
                return False

            pulp_task = modify_repo(
                self._pulp_client,
                pulp_repo,
                pulp_repo.latest_version_href,
                remove_content_units=packages_to_remove
            )
            self._task_stage_crud.update(
                task_stage,
                **{"detail": {
                        "msg": f"removing {len(packages_to_remove)}",
                        "task_href": pulp_task.pulp_href
                    }
                }
            )
            self._db.commit()
            return True
        except Exception:
            log.error("error occured trying to remove packages from repo")
            log.error(traceback.format_exc())
            if task_stage is None:
                task_stage = self._task_stage_crud.add(**{
                    "name": REMOVE_BANNED_PACKAGES_STAGE_NAME,
                    "task_id": task.id,
                    "error": {
                        "msg": "error occured trying to remove banned packages",
                        "detail": traceback.format_exc()
                    }
                })
            else:
                self._task_stage_crud.update(
                    task_stage,
                    **{
                        "error": {
                            "msg": "error occured trying to remove banned packages",
                            "detail": traceback.format_exc()
                        }
                    }
                )
            self._db.commit()
            raise

    def _start_publication(self, task: Task):
        """Starts the publication of the repo in the specified task. Raises
        an exception is any errors occured trying to start the sync

        :param task: Task entity which contains the details about the repo to publish
        :type task: Task
        :return: task_stage
        """

        pulp_repo = None
        task_stage = None
        log.debug(f"starting publication of repo with href {task.task_args['repo_href']}")
        try:
            pulp_repo = get_repo(self._pulp_client, task.task_args["repo_href"])
            log.debug(f"repo with href {task.task_args['repo_href']} is called {pulp_repo.name}")

            repo_type = get_repo_type_from_href(task.task_args["repo_href"])

            is_flat_repo = False

            if pulp_repo.remote and repo_type == "deb":
                pulp_remote = get_remote(self._pulp_client, pulp_repo.remote)
                is_flat_repo = pulp_remote.is_flat_repo

            pulp_manager = PulpManager(self._db, self._pulp_server.name)
            publication_task = pulp_manager.create_publication_from_repo_version(
                pulp_repo.latest_version_href, repo_type, is_flat_repo
            )

            #pylint: disable=duplicate-code
            task_stage = self._task_stage_crud.add(**{
                "name": PUBLISH_STAGE_NAME,
                "task_id": task.id,
                "detail": {
                    "msg": f"task in state {publication_task.state}",
                    "task_href": publication_task.pulp_href
                }
            })
            self._db.commit()
            log.debug(f"successfully started publication of {pulp_repo.name} "
                    f"with href {publication_task.pulp_href}")
            return task_stage
        except Exception:
            message = f"failed to start publication for repo {task.task_args['repo_href']}"
            if pulp_repo is not None:
                message = (f"failed to start publication for repo {pulp_repo.name} "
                        f"with href {task.task_args['repo_href']}")

            if task_stage is None:
                log.error(traceback.format_exc())
                task_stage = self._task_stage_crud.add(**{
                    "name": PUBLISH_STAGE_NAME,
                    "task_id": task.id,
                    "error": {
                        "msg": message,
                        "detail": traceback.format_exc()
                    }
                })
                self._task_crud.update(
                    task, **{
                        "state": "failed",
                        "date_finished": datetime.utcnow()
                    }
                )
                self._db.commit()
            raise

    def _publication_exists(self, repo_href: str):
        """Checks is a publication exists for the latest version of a repo. Returns bool
        indicating if it exists

        :param repo_href: href of repo to check if latest version of a repo is published
        :type reop_href: str
        :return: bool
        """

        repo = get_repo(self._pulp_client, repo_href)
        result = get_all_publications(
            self._pulp_client, params={"repository_version": repo.latest_version_href}
        )
        if len(result) == 0:
            return False
        return True

    #pylint: disable=too-many-return-statements,too-many-statements,too-many-branches
    def _progress_sync(self, task: Task, current_stage: TaskStage):
        """Checks the task being run by the current stage and sees if it has finished.
        If the current stage has finished and there are more stages to be run the next stage
        is kicked off. If all stages have been completed, or a stage has failed True is returned
        to indicate that the task has completed. False is returned when the task has not been
        completed, indicating that _progress_sync needs to be called again in the future

        :param task: The Task entity which represents the sync that is in progress
        :type task: Task
        :param current_stage: The current stage the running task is on
        :type current_stage: Task
        :return: bool
        """

        pulp_task = None
        current_stage_name = current_stage.name
        try:
            pulp_task = get_task(self._pulp_client, current_stage.detail["task_href"])
        except Exception:
            message = f"unexpected error retrieving task {current_stage.detail['task_href']}"
            log.error(message)
            log.error(traceback.format_exc())
            self._task_stage_crud.update(
                current_stage,
                **{
                    "error": {
                        "msg": message,
                        "detail": traceback.format_exc()
                    }
                }
            )
            self._task_crud.update(
                task, **{
                    "state": "failed",
                    "date_finished": datetime.utcnow()
                }
            )
            self._db.commit()
            return True

        if pulp_task.state not in ["running", "waiting"]:
            message = f"{current_stage_name} {pulp_task.state}. "
            detail = dict(current_stage.detail)
            detail["msg"] = message
            self._task_stage_crud.update(current_stage, **{"detail": detail})
            #pylint: disable=no-else-return
            if pulp_task.state != "completed":
                self._task_crud.update(
                    task, **{
                       "state": "failed",
                       "date_finished": datetime.utcnow()
                    }
                )
                self._db.commit()
                return True

            elif current_stage_name == SYNC_STAGE_NAME:
                try:
                    message = "no new packages were synched "
                    if len(pulp_task.created_resources) > 0:
                        message = f"created resources: {', '.join(pulp_task.created_resources)}"
                    detail = dict(current_stage.detail)
                    detail["msg"] = message
                    self._task_stage_crud.update(current_stage, **{"detail": detail})
                    self._db.commit()

                    if (not self._publication_exists(task.task_args["repo_href"])
                            and "/container/" not in task.task_args["repo_href"]):
                        started_package_removal = self._start_remove_banned_packages(task)
                        if not started_package_removal:
                            self._start_publication(task)
                    else:
                        message = dict(current_stage.detail)
                        detail["msg"] += " - no new publication required, "
                        detail["msg"] += "one exists for the current repo version, "
                        detail["msg"] += "or repo is of type container"
                        self._task_stage_crud.update(current_stage, **{"detail": detail})
                        self._task_crud.update(
                            task, **{"state": "completed", "date_finished": datetime.utcnow()}
                        )
                        self._db.commit()
                        return True
                except Exception:
                    # Only end up being here if db has fallen over, any other logging
                    # about what went wrong should end up in previous exceptions
                    log.error("unexpected error in sync stage")
                    log.error(traceback.format_exc())
                    # want this to be removed from the current running tasks
                    return True
            elif current_stage_name == REMOVE_BANNED_PACKAGES_STAGE_NAME:
                try:
                    detail = dict(current_stage.detail)
                    detail["msg"] = "banned packages removed successfully"
                    self._task_stage_crud.update(current_stage, **{"detail": detail})
                    self._start_publication(task)
                except Exception:
                    # Only end up being here if db has fallen over, any other logging
                    # about what went wrong should end up in previous exceptions
                    log.error("unexpected error in remove banned packages")
                    log.error(traceback.format_exc())
                    # want this to be removed from the current running tasks
                    return True
            else: # We are at the publish stage and everything is complete
                self._task_crud.update(
                    task, **{
                        "state": "failed" if pulp_task.state != "completed" else "completed",
                        "date_finished": datetime.utcnow()
                    }
                )
                self._db.commit()
                return True
        else:
            self._task_stage_crud.update(
                current_stage, **{"date_last_updated": datetime.utcnow()}
            )
            self._task_crud.update(task, **{"date_last_updated": datetime.utcnow()})
            self._db.commit()
        return False

    def _update_overall_sync_status(self, parent_task: Task, num_syncs_in_progress: int,
            num_syncs_completed: int, total_num_syncs: int):
        """Updates the task stage detail of the parent task with the overall status
        about number of syncs and those that have been completed.

        :param parent_task: parent task to update sync status of
        :type parent_task: Task
        :param num_syncs_in_progress: number of syncs in progress
        :type num_syncs_in_progress: int
        :param num_syncs_completed: number of syncs that have been completed
        :type num_syncs_completed: int
        :param total_num_syncs: total number of syncs
        :type total_num_syncs: int
        """

        parent_task_stage = parent_task.stages[-1]
        parent_task_stage_detail = parent_task_stage.detail
        message = (f"{num_syncs_in_progress} syncs in progress. "
                    f"{num_syncs_completed}/{total_num_syncs} syncs completed")
        parent_task_stage_detail["msg"] = message
        self._task_stage_crud.update(parent_task_stage, **{"detail": parent_task_stage_detail})
        self._db.commit()

    def _do_sync_repos(self, parent_task: Task, repo_tasks: List[Task], max_concurrent_syncs: int,
            sync_options: Dict=None):
        """Carries out the sync of the repos.

        :param parent_task: The parent task for the repo tasks that are about to be synched
        :type parent_task: Task
        :param repo_tasks: List of repo sync tasks to carry out
        :typerepo_tasks: List[Task]
        :param max_concurrent_syncs: Maximum number of syncs which should take place at once
        :type max_concurrent_syncs: int
        :param sync_options: Additional sync options to be set. These are repo type specific and
                             need to be looked up via the pulp API to see what is valid the group
                             of repos being synced
        :type sync_options: dict
        """

        self._task_stage_crud.add(**{
            "task_id": parent_task.id,
            "name": "sync repos"
        })
        self._db.commit()

        repo_tasks_pending = repo_tasks.copy()
        tasks_in_progress = {}

        while len(repo_tasks_pending) > 0 or len(tasks_in_progress) > 0:
            log.debug(f"checking/adding tasks repo_tasks_pending: {len(repo_tasks_pending)}, "
                        f"tasks_in_progress: {len(tasks_in_progress)}")

            while len(repo_tasks_pending) > 0 and len(tasks_in_progress) != max_concurrent_syncs:
                task = repo_tasks_pending.pop()
                tasks_in_progress[task.id] = task
                log.debug(f"task {task.name} added to list of tasks in progress")

            tasks_in_progress_copy = tasks_in_progress.copy()
            for task in tasks_in_progress_copy.values():
                self._db.refresh(task)
                if task.stages is None or len(task.stages) == 0:
                    try:
                        log.debug(f"starting sync for task {task.name} id {task.id}")
                        self._start_sync(task, sync_options)
                    except Exception:
                        if log.level == logging.DEBUG:
                            log.error(f"starting sync for task {task.name} id {task.id} failed")
                            log.error(traceback.format_exc())
                        del tasks_in_progress[task.id]

                if len(task.stages) > 0:
                    current_stage = task.stages[-1]
                    # When stages_complete is true means all stages have completed,
                    # or there was failure and no more stages progressed,
                    # in either case the task is considered as no longer being
                    # in progress
                    log.debug("progressing sync on task {task.name} with id {task.id}")
                    stages_complete = self._progress_sync(task, current_stage)
                    if stages_complete:
                        log.debug("task {task.name} with id {task.id} finished")
                        del tasks_in_progress[task.id]
                    else:
                        log.debug("task {task.name} with id {task.id} is still in progress")
                        self._task_stage_crud.update(
                            current_stage, **{"date_last_updated": datetime.utcnow()}
                        )
                        self._task_crud.update(task, **{"date_last_updated": datetime.utcnow()})
                        self._db.commit()
            #pylint: disable=line-too-long
            num_syncs_completed = len(repo_tasks) - (len(repo_tasks_pending) + len(tasks_in_progress))
            self._update_overall_sync_status(
                parent_task, len(tasks_in_progress), num_syncs_completed, len(repo_tasks)
            )

            # Skip the sleep if there are additional tasks that we can start
            if(len(tasks_in_progress) < max_concurrent_syncs and len(repo_tasks_pending) > 0):
                continue

            sleep(10)

        num_syncs_completed = len(repo_tasks) - (len(repo_tasks_pending) + len(tasks_in_progress))
        self._update_overall_sync_status(
            parent_task, len(tasks_in_progress), num_syncs_completed, len(repo_tasks)
        )
        self._db.commit()

    def _reconcile_repos(self, task: Task):
        """Reconciles repos that exist on the pulp server, so that an upto date list
        is known before the repos are synched.

        :param task: Task that resulted in the reconcile job being run
        :type task: Task
        :return: TaskStage
        """

        log.debug(f"starting reconcile of repos for {self._pulp_server.name}")
        pulp_reconciler = PulpReconciler(self._db, self._pulp_server.name)
        task_stage = self._task_stage_crud.add(**{
            "name": "reconcile repos",
            "detail": {"msg": "reconcile repos on pulp server"},
            "task_id": task.id
        })
        self._db.commit()

        try:
            pulp_reconciler.reconcile()
            self._task_stage_crud.update(
                task_stage, **{"detail": {"msg": "reconcile completed successfully"}}
            )
            self._db.commit()
            self._db.refresh(self._pulp_server)
            return task_stage
        except Exception:
            log.error("unexpected error in reconcile of repos")
            self._task_stage_crud.update(
                task_stage, **{
                    "error": {
                        "msg": "reconcile failed",
                        "detail": traceback.format_exc()
                    }
                }
            )
            self._db.commit()
            raise

    def _calculate_repo_health(self, task: Task, repos: List[PulpServerRepo]):
        """Calculates the repo health for the given list of repos

        :param task: Task entity associated with calculating repo health
        :type task: Task
        :param repos: List of PulpServerRepos to calculate repo health for
        :type repos: List[PulpserverRepo]
        """

        pulp_server_repo_crud = PulpServerRepoRepository(self._db)
        health_stage = self._task_stage_crud.add(**{
            "name": "calculate repo health",
            "task_id": task.id,
            "detail": {"msg": f"0/{len(repos)} complete"}
        })
        self._db.commit()
        count = 0
        try:
            for repo in repos:
                count += 1
                last_syncs = self._pulp_server_repo_task_crud.filter_paged(
                    page=1,
                    page_size=5,
                    eager=["task"],
                    **{
                        "pulp_server_repo_id": repo.id,
                        "sort_by": "date_created",
                        "order_by": "desc"
                    }
                )

                num_success = 0
                num_fail = 0

                for sync in last_syncs:
                    if sync.task.state != "completed":
                        num_fail += 1
                    else:
                        num_success +=  1

                if last_syncs[0].task.state == "completed":
                    pulp_server_repo_crud.update(repo, **{"repo_sync_health": "green"})
                elif num_fail <= 3 and num_success > 0:
                    pulp_server_repo_crud.update(repo, **{"repo_sync_health": "amber"})
                else:
                    pulp_server_repo_crud.update(repo, **{"repo_sync_health": "red"})
                pulp_server_repo_crud.update(repo, **{"repo_sync_health_date": datetime.now()})
                self._task_stage_crud.update(
                    health_stage, **{"detail": {"msg": f"{count}/{len(repos)} complete"}}
                )
                self._db.commit()
        except Exception:
            log.error("calculating repo health resulted in an unexpected error")
            log.error(traceback.format_exc())
            self._task_stage_crud.update(health_stage, **{
                "error": {
                    "msg": "calculating repo health resulted in an unexpected error",
                    "detail": traceback.format_exc()
                }
            })
            self._db.commit()
            raise

    def _calculate_pulp_server_repo_health_rollup(self, task: Task):
        """Calculates a health roll up for a pulp server based on all repos

        :param task: The task the server health rollup stage will be associated with
        :type task: Task
        """

        green = 0
        amber = 0
        red = 0

        health_stage = self._task_stage_crud.add(**{
            "name": "calculate pulp server repo health roll up",
            "task_id": task.id
        })
        self._db.commit()

        try:
            # could perhaps issue a sql alchmey query that does these counts
            # which would be quicker
            for repo in self._pulp_server.repos:
                if repo.repo_sync_health == "green":
                    green += 1
                elif repo.repo_sync_health == "amber":
                    amber += 1
                else:
                    red += 1

            if red > 0:
                self._pulp_server_crud.update(
                    self._pulp_server, **{"repo_sync_health_rollup": "red"}
                )
            elif amber > 0:
                self._pulp_server_crud.update(
                    self._pulp_server, **{"repo_sync_health_rollup": "amber"}
                )
            else:
                self._pulp_server_crud.update(
                    self._pulp_server, **{"repo_sync_health_rollup": "green"}
                )

            self._pulp_server_crud.update(
                self._pulp_server, **{"repo_sync_health_rollup_date": datetime.utcnow()}
            )
            self._db.commit()
        except Exception:
            log.error("calculating pulp search repo sync health rollup unexpected error")
            log.error(traceback.format_exc())
            self._task_stage_crud.update(health_stage, **{
                "error": {
                    "msg": "calculating pulp search repo sync health rollup unexpected error",
                    "detail": traceback.format_exc()
                }
            })
            self._db.commit()
            raise

    def create_task_entry(self, max_concurrent_syncs: int, regex_include: str=None,
            regex_exclude: str=None, source_pulp_server_name: str=None,
            sync_options: Dict=None):
        """Creates a task entry in the pulp manager database

        :param max_concurrent_syncs: Maximum number os repos that should be synced at once
        :type max_concurrent_syncs: int
        :param max_concurrent_syncs: Number of repos to sync at once
        :type max_concurrent_syncs: int
        :param regex_include: regex of repos to be included in the repo sync
        :type regex_include: str
        :param regex_exclude: regex of repos to exlude from the repo sync. If there are repos
                              that match both regex_exclude and regex_include, then regex_exclude
                              takes precendence and the repo is excluded from the sync
        :type regex_exclude: str
        :param source_pulp_server_name: the name of the pulp server repos are to be synched from.
                                        This is only needed when synching pulp slaves which don't
                                        sync repos from the internet
        :type source_pulp_server_name: str
        :param sync_options: Additional sync options to be set. These are repo type specific and
                             need to be looked up via the pulp API to see what is valid the group
                             of repos being synced
        :type sync_options: dict
        :return: Task
        """

        task_details = {
            "name": f"repo sync {self._pulp_server.name}",
            "task_type": "repo_group_sync",
            "task_args": {
                "name": self._pulp_server.name,
                "regex_include": regex_include,
                "regex_exclude": regex_exclude,
                "max_concurrent_syncs": max_concurrent_syncs,
                "source_pulp_server_name": source_pulp_server_name,
                "sync_options": sync_options
            }
        }

        if self._job_id:
            task_details.update({
                "date_started": datetime.utcnow(),
                "state": "running",
                "worker_name": socket.gethostname(),
                "worker_job_id": self._job_id
            })
        else:
            task_details.update({"state": "queued"})

        task = self._task_crud.add(**task_details)
        self._db.commit()
        return task


    def _get_task_entry(self, task_id: int):
        """Retrieves a task from the DB and updates it to set worker_name and worker_job_id.
        If the task is not found then 

        :param task_id: ID of task to retrieve from the DB
        :type task_id: int
        """

        task = self._task_crud.get_by_id(task_id)
        if task is None:
            raise PulpManagerTaskNotFoundError(f"task with id {task_id} not found")

        self._task_crud.update(task, **{
            "date_started": datetime.utcnow(),
            "state": "running",
            "worker_name": socket.gethostname(),
            "worker_job_id": self._job_id
        })

        self._db.commit()
        return task

    #pylint: disable=too-many-arguments
    def sync_repos(self, max_concurrent_syncs: int, regex_include: str=None,
            regex_exclude: str=None, source_pulp_server_name: str=None,
            sync_options: Dict=None, task_id=None):
        """Syncs the repos of the specified pulp server

        :param max_concurrent_syncs: Maximum number os repos that should be synced at once
        :type max_concurrent_syncs: int
        :param max_concurrent_syncs: Number of repos to sync at once
        :type max_concurrent_syncs: int
        :param regex_include: regex of repos to be included in the repo sync
        :type regex_include: str
        :param regex_exclude: regex of repos to exlude from the repo sync. If there are repos
                              that match both regex_exclude and regex_include, then regex_exclude
                              takes precendence and the repo is excluded from the sync
        :type regex_exclude: str
        :param source_pulp_server_name: the name of the pulp server repos are to be synched from.
                                        This is only needed when synching pulp slaves which don't
                                        sync repos from the internet
        :type source_pulp_server_name: str
        :param sync_options: Additional sync options to be set. These are repo type specific and
                             need to be looked up via the pulp API to see what is valid the group
                             of repos being synced
        :type sync_options: dict
        :param task_id: ID of an existing task to use to keep track of the repo sync
        :type task_id: int
        """

        task = None

        try:
            log.info(
                f"Starting sync repos for {self._pulp_server.name}, "
                f"max_concurrent_syncs {max_concurrent_syncs}, "
                f"regex_include {regex_include}, regex_exclude {regex_exclude}, "
                f"sync_options: {sync_options}, task_id: {task_id}"
            )

            if task_id is None:
                task = self.create_task_entry(
                    max_concurrent_syncs, regex_include, regex_exclude,
                    source_pulp_server_name, sync_options
                )
            else:
                task = self._get_task_entry(task_id)

            log.info(f"task_id for repo sync is {task_id}")
            log.info(f"reonciling repos on {self._pulp_server.name}")

            if source_pulp_server_name is not None:
                log.info(
                    f"{self._pulp_server.name} is set to sync from "
                    f"{source_pulp_server_name}, registering repos"
                )
                self._task_stage_crud.add(**{
                     "name": f"registering repos from {source_pulp_server_name}",
                     "task_id": task.id
                })
                self._db.commit()

                pulp_manager = PulpManager(self._db, self._pulp_server.name)
                pulp_manager.add_repos_from_pulp_server(
                    source_pulp_server_name, regex_include, regex_exclude
                )
                log.info(f"successfully registered repos from {source_pulp_server_name}")

            self._reconcile_repos(task)

            log.info(f"getting repos to sync for {self._pulp_server.name}")
            repos_to_sync = self._get_repos_to_sync(regex_include, regex_exclude)
            repo_tasks = self._generate_tasks(self._pulp_server.name, repos_to_sync, task.id)
            # reverse the list because we get last inserted task first which means
            # pulp manager would ned up processing the tasks backwards
            repo_tasks.reverse()

            log.info(f"starting repo syncs on {self._pulp_server.name}")
            self._do_sync_repos(task, repo_tasks, max_concurrent_syncs, sync_options)
            log.info(f"repo syncs completed for {self._pulp_server.name}")

            log.info(f"calcuting repo health for {self._pulp_server.name}")
            self._calculate_repo_health(task, repos_to_sync)
            log.info(f"repo health calculations complete for {self._pulp_server.name}")

            log.info(f"caulculating pulp server repo health rollup for {self._pulp_server.name}")
            self._db.refresh(self._pulp_server)
            self._calculate_pulp_server_repo_health_rollup(task)
            log.info(f"repo health calculations rollup complete for {self._pulp_server.name}")

            self._task_crud.update(
                task,
                **{
                    "state": "completed",
                    "date_finished": datetime.utcnow()
                }
            )

            self._db.commit()
        except PulpManagerTaskNotFoundError:
            log.error(f"repo sync failed, task_id {task_id} not found in db")
            log.error(traceback.format_exc())
            raise
        except Exception:
            log.error(f"unexpected error occured synching repos on {self._pulp_server.name}")
            log.error(traceback.format_exc())
            if task is not None:
                self._task_crud.update(
                    task,
                    **{
                        "state": "failed",
                        "date_finished": datetime.utcnow(),
                        "error": {
                            "msg": "unexpected error occured synching repos",
                            "detail": traceback.format_exc()
                        }
                    }
                )
                self._db.commit()
            raise

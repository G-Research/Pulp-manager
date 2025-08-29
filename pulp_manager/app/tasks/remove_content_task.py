"""Task for removing content from a repo
"""
from datetime import datetime
import socket
from time import sleep
import traceback

from rq import get_current_job
from pulp3_bindings.pulp3.remotes import get_remote
from pulp3_bindings.pulp3.repositories import get_repo, modify_repo
from pulp3_bindings.pulp3.resources import DebRepository
from pulp3_bindings.pulp3.tasks import get_task

from pulp_manager.app.database import session
from pulp_manager.app.exceptions import PulpManagerEntityNotFoundError, PulpManagerPulpTaskError
from pulp_manager.app.repositories import (
    PulpServerRepoRepository, TaskRepository, TaskStageRepository, PulpServerRepoTaskRepository
)
from pulp_manager.app.services import PulpManager
from pulp_manager.app.services.pulp_helpers import new_pulp_client, get_repo_type_from_href
from pulp_manager.app.utils import log


# pylint:disable=too-many-locals,too-many-branches,too-many-statements
def remove_repo_content(pulp_server_name: str, repo_name: str, content_href: str,
        task_id: int, force_publish: bool=False):
    """Task removes the specifies content unit from the specified repo. Removal is done
    from the latest version of the repo. If a new repo version is generated from the removal
    then the a new publication is created

    :param pulp_server_name: name of the pulp server to remove the repo content from
    :type pulp_server_name: str
    :param repo_name: name of the repo to remove the content unit from
    :type repo_name: str
    :param content_href: href of the ocntent unit to remove
    :type content_href: str
    :param task_id: ID of task to update status of in database
    :type task_id: int
    :param force_publish: force publish the latest version of the repo even if no
                          updates were made to the repo on Pulp
    :returns: Task
    """

    task = None
    task_crud = None
    try:
        db = session()
        pulp_server_repo_crud = PulpServerRepoRepository(db)
        task_crud = TaskRepository(db)
        task_stage_crud = TaskStageRepository(db)
        pulp_server_repo_task_crud = PulpServerRepoTaskRepository(db)
        pulp_manager = PulpManager(db, pulp_server_name)
        job = get_current_job()

        log.debug(f"retreiving task with {task_id}")
        task = task_crud.get_by_id(task_id)
        task_crud.update(
            task, **{
                "state": "running",
                "date_started": datetime.utcnow(),
                "worker_name": socket.gethostname(),
                "worker_job_id": job.id if job else None 
            })

        db.commit()

        log.debug(f"searching db for repo {repo_name} on {pulp_server_name}")
        task_stage_crud.add(**{
            "name": "finding repo on pulp server",
            "task_id": task.id
        })
        db.commit()

        pulp_server_repo_result = pulp_server_repo_crud.filter_join(True, **{
            "pulp_server_name": pulp_server_name, "name": repo_name
        })

        if len(pulp_server_repo_result) == 0:
            raise PulpManagerEntityNotFoundError(
                f"repo with name {repo_name} on pulp server {pulp_server_name} not found"
            )

        pm_pulp_server_repo = pulp_server_repo_result[0]
        log.debug(f"found pulp server repo with id {pm_pulp_server_repo.id}")
        pulp_server_repo_task_crud.add(**{
            "task_id": task.id, "pulp_server_repo_id": pm_pulp_server_repo.id
            })
        pulp_client = new_pulp_client(pm_pulp_server_repo.pulp_server)
        pulp_repo = get_repo(pulp_client, pm_pulp_server_repo.repo_href)

        modify_pulp_task = modify_repo(
            pulp_client, pulp_repo, pulp_repo.latest_version_href,
            remove_content_units=[content_href]
        )
        log.debug(f"modify task started with href {modify_pulp_task.pulp_href}")
        modify_stage = task_stage_crud.add(**{
            "name": "modifying repo content",
            "task_id": task.id,
            "detail": {
                "msg": f"task in state {modify_pulp_task.state}",
                "task_href": f"{modify_pulp_task.pulp_href} "
            }
        })
        db.commit()

        while modify_pulp_task.state in ["running", "waiting"]:
            sleep(10)
            modify_pulp_task = get_task(pulp_client, modify_pulp_task.pulp_href)
            task_stage_crud.update(modify_stage, **{
                "detail": {
                    "msg": f"task in state {modify_pulp_task.state}",
                    "task_href": f"{modify_pulp_task.pulp_href} "
                }
            })
            db.commit()

        log.debug(f"modify task {modify_pulp_task.pulp_href} end state {modify_pulp_task.state}")
        if modify_pulp_task.state != "completed":
            raise PulpManagerPulpTaskError(f"modify task {modify_pulp_task.pulp_href} failed")

        if len(modify_pulp_task.created_resources) == 0 and not force_publish:
            log.debug("repo publication step being skipped")
            task_stage_crud.add(**{
                "name": "repo publication skipped as no new resources created from modify",
                "task_id": task.id
            })
        else:
            is_flat_repo = False
            if isinstance(pulp_repo, DebRepository):
                pulp_remote = get_remote(pulp_client, pm_pulp_server_repo.remote_href)
                is_flat_repo = pulp_remote.is_flat_repo

            repo_version_to_publish = pulp_repo.latest_version_href
            if len(modify_pulp_task.created_resources) > 0:
                repo_version_to_publish = modify_pulp_task.created_resources[0]

            repo_type = get_repo_type_from_href(pulp_repo.pulp_href)
            publication_pulp_task = pulp_manager.create_publication_from_repo_version(
                repo_version_to_publish, repo_type, is_flat_repo
            )
            log.debug(f"publish task started with href {publication_pulp_task.pulp_href}")
            publication_stage = task_stage_crud.add(**{
                "name": f"publishing repo version {repo_version_to_publish}",
                "task_id": task.id,
                "detail": {
                    "msg": f"task in state {publication_pulp_task.state}",
                    "task_href": f"{publication_pulp_task.pulp_href} "
                }
            })
            db.commit()

            while publication_pulp_task.state in ["running", "waiting"]:
                sleep(10)
                publication_pulp_task = get_task(pulp_client, publication_pulp_task.pulp_href)
                task_stage_crud.update(publication_stage, **{
                    "detail": {
                        "msg": f"task in state {publication_pulp_task.state}",
                        "task_href": f"{publication_pulp_task.pulp_href} "

                    }
                })
                db.commit()

            log.debug(
                f"publish task {publication_pulp_task.pulp_href} "
                f"end state {publication_pulp_task.state}"
            )

            if publication_pulp_task.state != "completed":
                raise PulpManagerPulpTaskError(
                    f"publication task {publication_pulp_task.pulp_href} failed"
                )

        log.debug("remove repo content completed successfully")
        task_crud.update(task, **{
            "state": "completed",
            "date_finished": datetime.utcnow()
        })
        db.commit()
    except PulpManagerPulpTaskError as exception:
        log.error(f"Pulp task failed: {str(exception)}")
        if task_crud:
            task_crud.update(task, **{
                "state": "failed",
                "date_finished": datetime.utcnow(),
                "error": {"msg": str(exception)}
            })
        db.commit()
        raise
    except Exception as exception:
        log.error(f"unexpeted error ocurred in remove repo content: {str(exception)}")
        log.error(traceback.format_exc())
        if task_crud:
            task_crud.update(task, **{
                "state": "failed",
                "date_finished": datetime.utcnow(),
                "error": {
                    "msg": str(exception),
                    "detail": traceback.format_exc()
                }
            })
        db.commit()
        raise
    finally:
        db.close()

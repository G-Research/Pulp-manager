"""Scheduled repository removal task
"""

import traceback
from pulp_manager.app.database import session
from pulp_manager.app.services import RepoRemover
from pulp_manager.app.utils import log


def remove_repos(pulp_server: str, task_id: int, regex_include: str=None,
                 regex_exclude: str=None, dry_run: bool=False):
    """Task used to remove repositories based on regex patterns.

    :param pulp_server: Name of the Pulp server from which repos will be removed.
    :type pulp_server: str
    :param task_id: ID of the task this removal operation is related to.
    :type task_id: int
    :param regex_include: Regex pattern of repos to include in the removal.
    :type regex_include: str, optional
    :param regex_exclude: Regex pattern of repos to exclude from the removal. If there are repos
                          that match both regex_exclude and regex_include, regex_exclude takes
                          precedence and the repo is excluded from the removal.
    :type regex_exclude: str, optional
    :param dry_run: If true, the removal operation will be simulated without actually deleting
                    any repositories. Useful for testing and verification.
    :type dry_run: bool
    """

    try:
        db = session()
        repo_remover = RepoRemover(db, pulp_server)
        repo_remover.remove_repos(
            regex_include, regex_exclude, dry_run, task_id
        )
    except Exception:
        log.error("Unexpected error occurred during repository removal")
        log.error(f"Removal options pulp_server {pulp_server}, task_id {task_id}, "
                  f"dry_run {dry_run}, regex_include {regex_include}, "
                  f"regex_exclude {regex_exclude}")
        log.error(traceback.format_exc())
        raise
    finally:
        db.close()

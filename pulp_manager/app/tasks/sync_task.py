"""Scheduled sync task
"""

import traceback
from typing import Dict
from pulp_manager.app.database import session
from pulp_manager.app.services import RepoSyncher
from pulp_manager.app.utils import log


def sync_repos(pulp_server: str, max_concurrent_syncs: int, regex_include=None,
        regex_exclude=None, source_pulp_server_name: str=None,
        sync_options: Dict=None, task_id: int=None):
    """Task that is used to initiate the repo syncher

    :param pulp_server: name of the pulp server to sync jobs for
    :type pulp_server: str
    :param max_concurrent_syncs: number of repos that should be synched concurrently on
                                 the pulp server
    :type max_concurrent_syncs: int
    :param regex_include: regex of repos to include in the sync
    :type regex_include: str
    :param regex_exclude: regex of repos to exlude from the repo sync. If there are repos
                          that match both regex_exclude and regex_include, then regex_exclude
                          takes precendence and the repo is excluded from the sync
    :type regex_exclude: str
    :param source_pulp_server_name: the fqdn of the pulp server repos are to be synched from
    :type source_pulp_server_name: str
    :param sync_options: Additional sync options to be set. These are repo type specific and
                         need to be looked up via the pulp API to see what is valid the group
                         of repos being synced
    :type sync_options: dict
    :param task_id: task id that has already been queued to be updated for the sync task
    :type task_id: int
    """

    try:
        db = session()
        repo_syncher = RepoSyncher(db, pulp_server)
        repo_syncher.sync_repos(max_concurrent_syncs, regex_include, regex_exclude,
                source_pulp_server_name, sync_options, task_id)
    except Exception as exception:
        log.error("unexpected error occurred during synch of repos")
        log.error(f"sync options pulp_server {pulp_server}, max_concurrent_syncs "
                  f"{max_concurrent_syncs}, regex_include {regex_include}, regex_exclude "
                  f"{regex_exclude}, source_pulp_server_name {source_pulp_server_name}, "
                  f"sync_options {sync_options}, task_id {task_id}"
        )
        log.error(str(exception))
        log.error(traceback.format_exc())
        raise
    finally:
        db.close()

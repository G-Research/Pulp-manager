"""Scheduled sync task
"""

import traceback
from pulp_manager.app.database import session
from pulp_manager.app.services import Snapshotter
from pulp_manager.app.utils import log


def snapshot_repos(pulp_server: str, task_id: int, snapshot_prefix: str,
        allow_snapshot_reuse: bool, regex_include: str=None, regex_exclude: str=None):
    """Task that is used to initiate snpashots of repos

    :param pulp_server: name of the pulp server to sync jobs for
    :type pulp_server: str
    :param task_id: ID of task the snapshot is related to
    :type task_id: int
    :param regex_include: regex of repos to include in the snapshot
    :type regex_include: str
    :param regex_exclude: regex of repos to exlude from the sanpshot. If there are repos
                          that match both regex_exclude and regex_include, then regex_exclude
                          takes precendence and the repo is excluded from the snapshot
    :type regex_exclude: str
    """

    try:
        db = session()
        snapshotter = Snapshotter(db, pulp_server)
        snapshotter.snapshot_repos(
            snapshot_prefix, regex_include, regex_exclude, task_id, allow_snapshot_reuse
        )
    except Exception:
        log.error("unexpected error occurred during snapshot of repos")
        log.error(f"snapshot options pulp_server {pulp_server}, task_id {task_id}, "
                  f"snapshot_prefix {snapshot_prefix}, allow_snapshot_reuse {allow_snapshot_reuse} "
                  f" regex_include {regex_include}, regex_exclude {regex_exclude}"
        )
        log.error(traceback.format_exc())
        raise
    finally:
        db.close()

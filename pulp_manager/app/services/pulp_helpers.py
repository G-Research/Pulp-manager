"""Helpers for carry out common tasks on pulp
"""
import re
import os
from pulp3_bindings.pulp3 import Pulp3Client
from pulp3_bindings.pulp3.tasks import get_task,monitor_task
from pulp_manager.app.config import CONFIG
from pulp_manager.app.exceptions import PulpManagerValueError
from pulp_manager.app.models import PulpServer


def get_repo_type_from_href(pulp_href: str):
    """Returns the type of a repo from a pulp_href

    :param pulp_href: pulp href to extract repo type from
    :type pulp_href: str
    :return: str
    """

    repo_type_match = re.match('/pulp/api/v3/[a-z]+/([a-z]+)/', pulp_href)
    if repo_type_match and len(repo_type_match.groups()) > 0:
        return repo_type_match.groups()[0]

    raise PulpManagerValueError(f"repo type could not be determined from pulp_href {pulp_href}")


def get_pulp_server_repos(pulp_server: PulpServer, regex_include: str=None,
         regex_exclude: str=None, exclude_no_remote: bool=True):
    """Returns a list of PulpServerRepos that match the given regex requirements.

    :param pulp_server: PulpServer to get the repos from
    :type pulp_server: PulpServer
    :param regex_include: regex of repos to be included
    :type regex_include: str
    :param regex_exclude: regex of repos to exlude from the results. If there are repos
                          that match both regex_exclude and regex_include, then regex_exclude
                          takes precendence and the repo is excluded from the result
    :type regex_exclude: str
    :return: List[PulpServerRepo]
    """

    matching_repos = []
    for repo in pulp_server.repos:
        if exclude_no_remote and repo.remote_feed is None:
            continue
        #pylint: disable=no-else-continue
        repo_name = repo.repo.name
        if regex_exclude and re.search(regex_exclude, repo_name):
            continue
        elif regex_include and not re.search(regex_include, repo_name):
            continue
        elif regex_include and re.search(regex_include, repo_name):
            matching_repos.append(repo)
        else:
            matching_repos.append(repo)

    return matching_repos


def new_pulp_client(pulp_server: PulpServer):
    """Returns a new pulp3.Pulp3Client for interacting with the API

    Authenticates using password or vault based on 'Is_local' variable

    :param pulp_server: PulpServer entity to generate the client for
    :type pulp_server: PulpServer
    :return: pulp3.Pulp3Client
    """
    is_local = os.getenv('Is_local', 'false').lower() == 'true'

    if is_local:
        return Pulp3Client(
            pulp_server.name,
            username=pulp_server.username,
            password=CONFIG["pulp"]["password"],
            use_vault_agent=False,
            use_https=False
        )

    return Pulp3Client(
        pulp_server.name,
        username=pulp_server.username,
        use_vault_agent=True,
        vault_agent_addr=CONFIG["vault"]["vault_addr"],
        vault_svc_account_mount=pulp_server.vault_service_account_mount
    )


def delete_by_href(client: Pulp3Client, repo_href: str):
    """Deletes the pulp artifact identified by the href and returns the task object
    for monitoring.
    :param client: Instance of Pulp3Client to connect to API
    :type client: Pulp3Client
    :param repo_href: href of the artifact to delete
    :type repo_href: str
    :return: Task
    """
    if not isinstance(repo_href, str):
        raise ValueError(
            f"Expected type str for repo_href, got {type(repo_href)}"
        )

    result = client.delete(repo_href)
    return get_task(client, result['task'])

def delete_by_href_monitor(client: Pulp3Client, repo_href: str, poll_interval_sec: int = 1,
                           max_wait_count: int = 200, error: bool = True):
    """Deletes the artifact identified by the href and monitors the task for completion.
    Returns the Task object on completion.
    :param client: Client to connect to the API with
    :type client: Pulp3Client
    :param repo_href: href of the artifact to delete
    :type repo_href: str
    :param poll_interval_sec: Number of seconds to wait between polling the API
    :type poll_interval_sec: int
    :param max_wait_count: Maximum number of times to wait for the task to enter the
                           running state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """
    task = delete_by_href(client, repo_href)
    return monitor_task(client, task.pulp_href, poll_interval_sec, max_wait_count, error)

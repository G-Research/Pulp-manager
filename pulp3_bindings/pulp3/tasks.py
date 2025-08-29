"""Methods for interacting with tasks
"""

from time import sleep
from typing import List
from pydantic import parse_obj_as
from .client import Pulp3Client
from .exceptions import PulpV3InvalidTypeError, PulpV3TaskFailed, PulpV3TaskStuckWaiting
from .resources import Task


BASE_URL = '/tasks/'


def _validate_href(href: str):
    """Carries out some basic tasks to make sure a href is valid for a task.
    Raises PulpV3InvalidTypeError if invalid href is given
    :param href: href to validate
    :type href: str
    """

    if 'tasks' not in href:
        raise PulpV3InvalidTypeError('href is not valid for a task')


def get_all_tasks(client: Pulp3Client, params: dict=None):
    """Retrieves all tasks
    :param client: Instance of Pulp3Client to connect to API with
    :type client: Pulp3Client
    :param params: dict of arguments to user to filter tasks to return
    :type params: dict
    :return: List of tasks
    """

    tasks = client.get_page_results(BASE_URL, params=params)
    return parse_obj_as(List[Task], tasks)


def get_task(client: Pulp3Client, href: str):
    """Returns the specified task
    :param client: Instance of Pulp3Client to connect to API with
    :type client: Pulp3Client
    :param href: href of task to retireve
    :type href: str
    :return: Task
    """

    _validate_href(href)
    result = client.get(href)
    return parse_obj_as(Task, result)


def update_task(client: Pulp3Client, href: str, state: str):
    """Updates the task with the given state
    :param Pulp3Client: Instance of Pulp3Client to connect to API with
    :type client: Pulp3Client
    :param href: href of task to update
    :type href: str
    :param state: state to put task into
    :type state: str
    :return: Task
    """

    _validate_href(href)
    result = client.patch(href, {'state': state})
    return parse_obj_as(Task, result)


def monitor_task(client: Pulp3Client, href: str, poll_interval_sec: int = 15,
        max_wait_count: int = 200, error=True):
    """Monitors the given task to completeion/failure and returns the task object.
    Waits for the task to start running, teh defaults mean there is a wait
    time of 50 minutes for the task. If the task fails to start then
    PulpV3TaskStuckWaiting is raised
    :param client: Instance of Pulp3Client to connect to API with
    :type client: Pulp3Client
    :param href: Task of href to monitor
    :type href: str
    :param poll_interval_sec: Number of seconds that should be between monitoring of the task
                              to see if it has finished
    :type poll_interval_sec: int
    :param max_wait_count: Number of retires that should be carried out before failing
                           raising an exception because the task did not come out of
                           a waiting state
    :type max_wait_count: int
    :param error: Raise error if task enters failed state. Default True
    :type error: bool
    :return: Task
    """

    _validate_href(href)
    task = get_task(client, href)
    wait_count = 0

    while task.state in ['running', 'waiting']:
        if task.state == 'waiting':
            wait_count += 1
        if wait_count == max_wait_count:
            raise PulpV3TaskStuckWaiting(
                'Task {0} failed to enter running state. Poll interval: {1}, wait count: {2}'.format(
                    href, poll_interval_sec, max_wait_count
                )
            )
        sleep(poll_interval_sec)
        task = get_task(client, href)

    if task.state == 'failed' and error:
        error_string = ""
        for key, value in task.error.items():
            error_string += "{0}: {1}".format(key, value)

        raise PulpV3TaskFailed("Task {0} failed with errors: {1}".format(href, error_string))

    return task

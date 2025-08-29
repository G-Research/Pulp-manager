import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import (
    Pulp3Client, PulpV3InvalidTypeError, PulpV3TaskFailed, PulpV3TaskStuckWaiting
)
from pulp3_bindings.pulp3.resources import Task
from pulp3_bindings.pulp3.tasks import (
    _validate_href, get_all_tasks, get_task, update_task, monitor_task
)


class TestTasks:
    """Tests for tasks api methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    def test_validate_href_ok(self):
        """Tests that a valid tasks href doesn't result in error
        """

        _validate_href('/tasks/')

    def test_validate_href_fail(self):
        """Tests invalid task href results in exception
        """

        with pytest.raises(PulpV3InvalidTypeError):
            _validate_href('/tasking/')

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_tasks(self, mock_get_page_results):
        """Tests that when multiple tasks are returned two task objects are returned in a list
        """

        mock_result = [
            {
                'pulp_href': '/tasks/1/',
                'pulp_created': datetime.now(),
                'state': 'completed',
                'name': 'sync task',
                'logging_cid': 'abc'
            },
            {
                'pulp_href': '/tasks/2/',
                'pulp_created': datetime.now(),
                'state': 'completed',
                'name': 'sync task',
                'logging_cid': 'def'
            },
        ]

        mock_get_page_results.return_value = mock_result
        result = get_all_tasks(self.client)
        assert isinstance(result[0], Task)
        assert result[0].pulp_href == '/tasks/1/'
        assert result[1].pulp_href == '/tasks/2/'

    @patch('pulp3.Pulp3Client.get')
    def test_get_task(self, mock_get):
        """Tests that a single task object is returned
        """

        mock_result = {
            'pulp_href': '/tasks/1/',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'sync task',
            'logging_cid': 'abc'
        }

        mock_get.return_value = mock_result
        result = get_task(self.client, '/tasks/1/')
        assert isinstance(result, Task)
        assert result.pulp_href == '/tasks/1/'

    @patch('pulp3.Pulp3Client.patch')
    def test_update_task(self, mock_patch):
        """Tests that patching a task returns a task in the new state
        """

        mock_result = {
            'pulp_href': '/tasks/1/',
            'pulp_created': datetime.now(),
            'state': 'cancelled',
            'name': 'sync task',
            'logging_cid': 'abc'
        }

        mock_patch.return_value = mock_result
        result = update_task(self.client, '/tasks/1/', 'cancelled')
        patch_args, patch_kwargs = mock_patch.call_args
        assert patch_args[0] == '/tasks/1/'
        assert patch_args[1] == {'state': 'cancelled'}
        assert isinstance(result, Task)
        assert result.state == 'cancelled'

    @patch('pulp3.Pulp3Client.get')
    @patch('pulp3.tasks.sleep')
    def test_monitor_task_ok(self, mock_sleep, mock_get):
        """Tests that when a task completes with no errors
        the task object is returned
        """

        mock_tasks = [
            {
                'pulp_href': '/tasks/1/',
                'pulp_created': datetime.now(),
                'state': 'waiting',
                'name': 'sync task',
                'logging_cid': 'abc'
            },
            {
                'pulp_href': '/tasks/1/',
                'pulp_created': datetime.now(),
                'state': 'waiting',
                'name': 'sync task',
                'logging_cid': 'abc'
            },
            {
                'pulp_href': '/tasks/1/',
                'pulp_created': datetime.now(),
                'state': 'running',
                'name': 'sync task',
                'logging_cid': 'abc'
            },
            {
                'pulp_href': '/tasks/1/',
                'pulp_created': datetime.now(),
                'state': 'finished',
                'name': 'sync task',
                'logging_cid': 'abc'
            }
        ]

        def sleep(seconds):
            pass

        def get(href, params=None):
            return mock_tasks.pop(0)

        mock_sleep.side_effect = sleep
        mock_get.side_effect = get

        result = monitor_task(self.client, '/tasks/1/')
        assert isinstance(result, Task)
        assert result.state == 'finished'
        assert mock_get.call_count == 4
        assert mock_sleep.call_count == 3

    @patch('pulp3.Pulp3Client.get')
    def test_monitor_task_fail_exception(self, mock_get):
        """Tests that when a task fails to complete an excpetion is thrown
        """

        mock_get.return_value = {
            'pulp_href': '/tasks/1/',
            'pulp_created': datetime.now(),
            'state': 'failed',
            'error': {'error': 'task failed'},
            'name': 'sync task',
            'logging_cid': 'abc'
        }

        with pytest.raises(PulpV3TaskFailed):
            monitor_task(self.client, '/tasks/1/')

    @patch('pulp3.Pulp3Client.get')
    def test_monitor_task_fail_no_exception(self, mock_get):
        """Tests that when a task fails to complete an excpetion is not thrown
        and the task object is returned
        """

        mock_get.return_value = {
            'pulp_href': '/tasks/1/',
            'pulp_created': datetime.now(),
            'state': 'failed',
            'error': {'error': 'task failed'},
            'name': 'sync task',
            'logging_cid': 'abc'
        }

        result = monitor_task(self.client, '/tasks/1/', error=False)
        assert result.state == 'failed'

    @patch('pulp3.Pulp3Client.get')
    @patch('pulp3.tasks.sleep')
    def test_monitor_task_waiting_exception(self, mock_sleep, mock_get):
        """Tests that when a task fails to move from waiting state an excpetion is thrown
        """

        mock_get.return_value = {
            'pulp_href': '/tasks/1/',
            'pulp_created': datetime.now(),
            'state': 'waiting',
            'error': {'error': 'task failed'},
            'name': 'sync task',
            'logging_cid': 'abc'
        }

        with pytest.raises(PulpV3TaskStuckWaiting):
            monitor_task(self.client, '/tasks/1/', max_wait_count=5)
            assert mock_sleep.call_count == 5

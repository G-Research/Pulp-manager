import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client, PulpV3InvalidTypeError, PulpV3InvalidArgumentError
from pulp3_bindings.pulp3.remotes import (
    REMOTE_INVALID_CREATION_FIELDS, remove_invalid_creation_fields, get_remote_class,
    get_all_remotes, get_remote, new_remote, update_remote, update_remote_monitor,
    delete_remote, delete_remote_monitor
)
from pulp3_bindings.pulp3.resources import (
    Task, Remote, FileRemote, RpmRemote, DebRemote, PythonRemote, ContainerRemote
)


class TestRemotes:
    """Tests for remote api methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    def test_remove_invalid_creation_fields(self):
        """Tests that invalid fields for creation are removed when dict object returned
        """

        remote = RpmRemote(**{
            'name': 'test-remote',
            'url': 'https://someurl.domain.local',
            'policy': 'immediate',
            'pulp_href': 'fake_value',
            'pulp_created': datetime.now(),
            'versions_href': 'fake_value',
            'hidden_fields': [],
            'pulp_last_updated': datetime.now()
        })

        result = remove_invalid_creation_fields(remote)
        for invalid_field in REMOTE_INVALID_CREATION_FIELDS:
            assert invalid_field not in result

    def test_get_remote_class(self):
        """Tests that the correct remote class is given for the specified type
        """

        assert get_remote_class('file') == FileRemote
        assert get_remote_class('rpm') == RpmRemote
        assert get_remote_class('deb') == DebRemote
        assert get_remote_class('python') == PythonRemote
        assert get_remote_class('container') == ContainerRemote

    def test_get_remote_class_fail(self):
        """Tests PulpV3InvalidArgumentError raised when invalid type is specified
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_remote_class('invalid')

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_remotes(self, mock_get_page_results):
        """Tests a list of remotes are returned
        """

        mock_get_page_results.return_value = [
            {
                'name': 'test-remote',
                'url': 'https://someurl.domain.local',
                'policy': 'immediate',
                'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
                'pulp_created': datetime.now(),
                'versions_href': 'fake_value',
                'pulp_last_updated': datetime.now()
            },
            {
                'name': 'test-remote2',
                'url': 'https://someurl.domain.local',
                'policy': 'immediate',
                'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/456/',
                'pulp_created': datetime.now(),
                'versions_href': 'fake_value',
                'pulp_last_updated': datetime.now()
            }
        ]

        result = get_all_remotes(self.client)
        assert len(result) == 2
        assert isinstance(result[0], Remote)
        assert result[0].name == 'test-remote'
        assert result[1].name == 'test-remote2'

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_specific(self, mock_get_page_results):
        """Tests when a specified type of remote is requested that is returned
        """

        mock_get_page_results.return_value = [
            {
                'name': 'test-remote',
                'url': 'https://someurl.domain.local',
                'policy': 'immediate',
                'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
                'pulp_created': datetime.now(),
                'versions_href': 'fake_value',
                'pulp_last_updated': datetime.now()
            },
            {
                'name': 'test-remote2',
                'url': 'https://someurl.domain.local',
                'policy': 'immediate',
                'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/456/',
                'pulp_created': datetime.now(),
                'versions_href': 'fake_value',
                'pulp_last_updated': datetime.now()
            }
        ]

        result = get_all_remotes(self.client, 'rpm')
        assert isinstance(result[0], RpmRemote)

    def test_get_all_invalid(self):
        """Tests that when an invalid remote type is specified an excpetion is thrown
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_all_remotes(self.client, 'rpmzzz')

    @patch('pulp3.Pulp3Client.get')
    def test_get_remote(self, mock_get):
        """Tests that when a href is specified an instance of a remote is returned
        """

        mock_get.return_value = {
            'name': 'test-remote',
            'url': 'https://someurl.domain.local',
            'policy': 'immediate',
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'versions_href': 'fake_value',
            'pulp_last_updated': datetime.now()
        }

        result = get_remote(self.client, '/pulp/api/v3/remotes/rpm/rpm/123/')
        assert isinstance(result, RpmRemote)

    def test_get_remote_invalid(self):
        """Tests PulpV3InvalidArgumentError is raised for unsupported remote href
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_remote(self.client, '/pulp/api/v3')

    @patch('pulp3.Pulp3Client.post')
    def test_new_remote_rpm(self, mock_post):
        """Tests create a new remote rpm updates the object passed through
        """

        mock_post.return_value = {
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        }

        remote = RpmRemote(**{
            'name': 'test-repo', 'url': 'https://test.domain.local', 'policy': 'immediate'
        })

        new_remote(self.client, remote)
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/remotes/rpm/rpm/'
        assert remote.pulp_href is not None
        assert remote.pulp_created is not None

    @patch('pulp3.Pulp3Client.post')
    def test_new_remote_deb(self, mock_post):
        """Tests create a new remote deb updates the object passed through
        """

        mock_post.return_value = {
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate',
            'distributions': 'focal'
        }

        remote = DebRemote(**{
            'name': 'test-repo',
            'url': 'https://test.domain.local',
            'policy': 'immediate',
            'distributions': 'focal'
        })

        new_remote(self.client, remote)
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/remotes/deb/apt/'
        assert remote.pulp_href is not None
        assert remote.pulp_created is not None

    @patch('pulp3.Pulp3Client.post')
    def test_new_remote_file(self, mock_post):
        """Tests create a new remote file updates the object passed through
        """

        mock_post.return_value = {
            'pulp_href': '/pulp/api/v3/remotes/file/file/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        }

        remote = FileRemote(**{
            'name': 'test-repo', 'url': 'https://test.domain.local', 'policy': 'immediate'
        })

        new_remote(self.client, remote)
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/remotes/file/file/'
        assert remote.pulp_href is not None
        assert remote.pulp_created is not None

    @patch('pulp3.Pulp3Client.post')
    def test_new_remote_python(self, mock_post):
        """Tests create a new remote python updates the object passed through
        """

        mock_post.return_value = {
            'pulp_href': '/pulp/api/v3/remotes/python/python/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        }

        remote = PythonRemote(**{
            'name': 'test-repo', 'url': 'https://test.domain.local', 'policy': 'immediate'
        })

        new_remote(self.client, remote)
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/remotes/python/python/'
        assert remote.pulp_href is not None
        assert remote.pulp_created is not None

    @patch('pulp3.Pulp3Client.post')
    def test_new_remote_container(self, mock_post):
        """Tests create a new remote container updates the object passed through
        """

        mock_post.return_value = {
            'pulp_href': '/pulp/api/v3/remotes/python/python/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate',
            'upstream_name': 'pulp'
        }

        remote = ContainerRemote(**{
            'name': 'test-repo',
            'url': 'https://test.domain.local',
            'policy': 'immediate',
            'upstream_name': 'pulp'
        })

        new_remote(self.client, remote)
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/remotes/container/container/'
        assert remote.pulp_href is not None
        assert remote.pulp_created is not None

    @patch('pulp3.Pulp3Client.patch')
    @patch('pulp3.remotes.get_task')
    def test_update_remote(self, mock_get_task, mock_patch):
        """Tests updating a remote returns a task object to monitor progress
        """

        mock_patch.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        remote = RpmRemote(**{
            'name': 'test-repo', 'url': 'https://test.domain.local', 'policy': 'immediate'
        })

        result = update_remote(self.client, remote)
        assert isinstance(result, Task)

    @patch('pulp3.remotes.update_remote')
    @patch('pulp3.remotes.monitor_task')
    @patch('pulp3.remotes.get_remote')
    def test_update_remote_monitor(self, mock_get_remote, mock_monitor_task, mock_update_remote):
        """Tests that the remote object is updated when the task is monitored to completion
        """

        mock_update_remote.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        mock_get_remote.return_value = RpmRemote(**{
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo-updated',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        })

        remote = RpmRemote(**{
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        })

        update_remote_monitor(self.client, remote)
        assert remote.name == 'test-repo-updated'

    @patch('pulp3.Pulp3Client.delete')
    @patch('pulp3.remotes.get_task')
    def test_delete_remote(self, mock_get_task, mock_delete):
        """Tests deleteing a remote returns a task object to monitor progress
        """

        mock_delete.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-task',
            'logging_cid': '1234'
        })

        remote = RpmRemote(**{
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'name': 'test-repo',
            'url': 'https://test.domain.local',
            'policy': 'immediate'
        })

        result = delete_remote(self.client, remote)
        assert isinstance(result, Task)

    @patch('pulp3.remotes.delete_remote')
    @patch('pulp3.remotes.monitor_task')
    def test_delete_remote_monitor(self, mock_monitor_task, mock_delete_remote):
        """Tests that when the remote object is delete when the task of completion is returned
        """

        mock_delete_remote.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        remote = RpmRemote(**{
            'pulp_href': '/pulp/api/v3/remotes/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'test-repo',
            'url': 'https://test.domain.local', 
            'policy': 'immediate'
        })

        result = delete_remote_monitor(self.client, remote)
        assert isinstance(result, Task)
        assert result.state == 'completed'


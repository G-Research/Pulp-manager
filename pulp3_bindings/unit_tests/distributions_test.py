import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client, PulpV3InvalidTypeError, PulpV3InvalidArgumentError
from pulp3_bindings.pulp3.distributions import (
    DISTRIBUTION_INVALID_CREATION_FIELDS, remove_invalid_creation_fields, get_distribution_class,
    get_all_distributions, get_distribution, new_distribution, new_distribution_monitor,
    update_distribution, update_distribution_monitor, delete_distribution,
    delete_distribution_monitor
)
from pulp3_bindings.pulp3.resources import (
    Task, Distribution, FileDistribution, RpmDistribution, DebDistribution, PythonDistribution,
    ContainerDistribution
)


class TestDistributions:
    """Tests for publication api methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    def test_remove_invalid_creation_fields(self):
        """Tests that fields not allowed in distribution creation/update are removed
        """

        distribution = Distribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "pulp_created": "2023-08-17T14:25:54.599108Z",
            "name": "test-publication",
            "base_path": "el7-x86_64/test-publication",
            "repository": "/pulp/api/v3/repositories/rpm/rpm/123/",
        })

        result = remove_invalid_creation_fields(distribution)
        for field in DISTRIBUTION_INVALID_CREATION_FIELDS:
            assert field not in result

    def test_get_distribution_class(self):
        """Checks the correct distribution class is returned for the distribution type
        """

        assert get_distribution_class('file') == FileDistribution
        assert get_distribution_class('rpm') == RpmDistribution
        assert get_distribution_class('deb') == DebDistribution
        assert get_distribution_class('python') == PythonDistribution
        assert get_distribution_class('container') == ContainerDistribution

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_distributions(self, mock_get_page_results):
        """Tests that List of type Distribution is returned
        """

        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
                "pulp_created": "2023-07-27T08:07:24.555514Z",
                "base_path": "rpm/centos9-x86_64/ext-centos9-stream-highavailability",
                "content_guard": None,
                "hidden": False,
                "pulp_labels": {},
                "name": "ext-centos9-stream-highavailability",
                "repository": None
            },
            {
                "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
                "pulp_created": "2023-07-24T13:42:59.561576Z",
                "base_path": "rpm/centos8-x86_64/ext-centos8-stream-advanced-virtualization",
                "content_guard": None,
                "hidden": False,
                "pulp_labels": {},
                "name": "ext-centos8-stream-advanced-virtualization",
                "repository": None
            }
        ]

        result = get_all_distributions(self.client)
        assert len(result) == 2
        assert isinstance(result[0], Distribution)

    @patch('pulp3.Pulp3Client.get')
    def test_get_distribution(self, mock_get):
        """Tests that a distribution of the correct type is returned
        """

        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "pulp_created": "2023-07-27T08:07:24.555514Z",
            "base_path": "rpm/centos9-x86_64/ext-centos9-stream-highavailability",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "ext-centos9-stream-highavailability",
            "repository": None
        }

        result = get_distribution(self.client, '/pulp/api/v3/distributions/rpm/rpm/123/')
        assert isinstance(result, RpmDistribution)

    @patch('pulp3.Pulp3Client.post')
    @patch('pulp3.distributions.get_task')
    def test_new_distribution(self, mock_get_task, mock_post):
        """Tests that when a new distribution is created a task object is returned for monitoring
        """
        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'new-distribution-task',
            'logging_cid': '1234'
        })

        distribution = RpmDistribution(**{
        "base_path": "rpm/centos8-x86_64/ext-centos8-stream-advanced-virtualization",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "ext-centos8-stream-advanced-virtualization",
            "repository": None
        })
 
        result = new_distribution(self.client, distribution)
        assert isinstance(result, Task)

    @patch('pulp3.Pulp3Client.post')
    @patch('pulp3.distributions.get_task')
    def test_new_distribution_url_test(self, mock_get_task, mock_post):
        """Tests correct urls are posted to for different distribution types
        """
        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'new-distribution-task',
            'logging_cid': '1234'
        })

        distribution = FileDistribution(**{
        "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })
        result = new_distribution(self.client, distribution)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/distributions/file/file/'

        distribution = RpmDistribution(**{
        "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })
        result = new_distribution(self.client, distribution)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/distributions/rpm/rpm/'

        distribution = DebDistribution(**{
        "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })
        result = new_distribution(self.client, distribution)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/distributions/deb/apt/'

        distribution = PythonDistribution(**{
        "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })
        result = new_distribution(self.client, distribution)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/distributions/python/pypi/'

        distribution = ContainerDistribution(**{
        "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })
        result = new_distribution(self.client, distribution)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/distributions/container/container/'

    @patch('pulp3.distributions.new_distribution')
    @patch('pulp3.distributions.monitor_task')
    @patch('pulp3.distributions.get_distribution')
    def test_new_distribution_monitor(self, mock_get_distribution, mock_monitor_task,
            mock_new_distribution):
        """Tests when new_distribution_monitor completes successfully the distribution object
        is updated
        """

        mock_new_distribution.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'new-distribution-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'new-distribution-task',
            'logging_cid': '1234',
            'created_resources': ['/pulp/api/v3/distributions/rpm/rpm/123/']
        })

        mock_get_distribution.return_value = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        distribution = RpmDistribution(**{
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        assert distribution.pulp_href is None
        new_distribution_monitor(self.client, distribution)
        assert distribution.pulp_href is not None

    @patch('pulp3.Pulp3Client.patch')
    @patch('pulp3.distributions.get_task')
    def test_update_distribution(self, mock_get_task, mock_patch):
        """Tests that when a distribution is updated a task object is returned to monitor progress
        """

        mock_patch.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-distribution-task',
            'logging_cid': '1234'
        })

        distribution = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        result = update_distribution(self.client, distribution)
        assert isinstance(result, Task)

    @patch('pulp3.distributions.update_distribution')
    @patch('pulp3.distributions.monitor_task')
    @patch('pulp3.distributions.get_distribution')
    def test_update_distribution_monitor(self, mock_get_distribution, mock_monitor_task,
            mock_update_distribution):
        """Tests that when update_distribution_monitor completes successfully the distribution
        object passed through is updated
        """

        mock_update_distribution.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-distribution-task',
            'logging_cid': '1234'
        })

        mock_get_distribution.return_value = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo-updated",
            "repository": None
        })

        distribution = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        update_distribution_monitor(self.client, distribution)
        assert distribution.name == 'test-repo-updated'

    @patch('pulp3.Pulp3Client.delete')
    @patch('pulp3.distributions.get_task')
    def test_delete_distribution(self, mock_get_task, mock_delete):
        """Tests that calling delete on repo results in a Task object being returned
        """
        mock_delete.return_value = {'task': '/pulp/api/v3/tasks/123'}

        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-distribution-task',
            'logging_cid': '1234'
        })

        distribution = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        result = delete_distribution(self.client, distribution)
        assert isinstance(result, Task)

    @patch('pulp3.distributions.delete_distribution')
    @patch('pulp3.distributions.monitor_task')
    def test_delete_distribution_monitor(self, mock_monitor_task, mock_delete_distribution):
        """Tests that completed task object is returned when delete has finished
        """

        mock_delete_distribution.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-distribution-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'delete-distribution-task',
            'logging_cid': '1234'
        })

        distribution = RpmDistribution(**{
            "pulp_href": "/pulp/api/v3/distributions/rpm/rpm/123/",
            "date_created": datetime.now(),
            "base_path": "rpm/test-repo",
            "content_guard": None,
            "hidden": False,
            "pulp_labels": {},
            "name": "test-repo",
            "repository": None
        })

        result = delete_distribution_monitor(self.client, distribution)
        assert isinstance(result, Task)
        assert result.state == 'completed'

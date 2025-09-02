import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client, PulpV3InvalidTypeError, PulpV3InvalidArgumentError
from pulp3_bindings.pulp3.publications import (
    PUBLICATION_INVALID_CREATION_FIELDS, remove_invalid_creation_fields, get_publication_class,
    get_all_publications, get_publication, new_publication, new_publication_monitor,
    delete_publication, delete_publication_monitor
)
from pulp3_bindings.pulp3.resources import (
    Task, Publication, FilePublication, RpmPublication, DebPublication, PythonPublication
)


class TestPublications:
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
        """Tests that fields not allowed in publication creation/update are removed
        """

        publication = Publication(**{
            "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
            "pulp_created": "2023-08-17T14:25:54.599108Z",
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/123/versions/2/",
        })

        result = remove_invalid_creation_fields(publication) 
        for field in PUBLICATION_INVALID_CREATION_FIELDS:
            assert field not in result

    def test_get_publication_class(self):
        """Tests the correct class is returned for the specified publication type
        """

        assert get_publication_class('file') == FilePublication
        assert get_publication_class('rpm') == RpmPublication
        assert get_publication_class('deb') == DebPublication
        assert get_publication_class('python') == PythonPublication

    def test_get_publication_class_fail(self):
        """Tests that when an incorrect publication class is specified PulpV3InvalidArgumentError
        is raised
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_publication_class('container')

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_publications(self, mock_get_page_results):
        """Tests that getting all paged results and not limiting the type resturns
        a List of type Publication
        """

        mock_get_page_results.return_value = [
            {
               "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
               "pulp_created": "2023-08-17T14:25:54.599108Z",
               "repository_version": "/pulp/api/v3/repositories/rpm/rpm/123/versions/2/",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/123/"
            },
            {
                "pulp_href": "/pulp/api/v3/publications/rpm/rpm/456/",
                "pulp_created": "2023-08-17T14:25:04.743501Z",
                "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/456/"
            }
        ]

        result = get_all_publications(self.client)
        assert len(result) == 2
        assert isinstance(result[0], Publication)

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_publications_type(self, mock_get_page_results):
        """Tests that when the type of publication is specified, those objects are returned
        """

        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
                "pulp_created": "2023-08-17T14:25:54.599108Z",
                "repository_version": "/pulp/api/v3/repositories/rpm/rpm/123/versions/2/",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/123/",
                "metadata_checksum_type": "sha256",
                "package_checksum_type": "sha256",
                "gpgcheck": 1,
                "repo_gpgcheck": 0,
                "sqlite_metadata": False
            },
            {
                "pulp_href": "/pulp/api/v3/publications/rpm/rpm/456/",
                "pulp_created": "2023-08-17T14:25:04.743501Z",
                "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
                "repository": "/pulp/api/v3/repositories/rpm/rpm/456/",
                "metadata_checksum_type": "sha256",
                "package_checksum_type": "sha256",
                "gpgcheck": 1,
                "repo_gpgcheck": 0,
                "sqlite_metadata": False
            }
        ]

        result = get_all_publications(self.client, 'rpm')
        call_args, call_kwargs = mock_get_page_results.call_args

        assert call_args[0] == '/publications/rpm/rpm/'
        assert isinstance(result[0], RpmPublication)

    @patch('pulp3.Pulp3Client.get')
    def test_get_publication(self, mock_get):
        """Tests that publication returns the create type of object
        """

        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
            "pulp_created": "2023-08-17T14:25:54.599108Z",
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/123/versions/2/",
            "repository": "/pulp/api/v3/repositories/rpm/rpm/123/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        }

        result = get_publication(self.client, '/pulp/api/v3/publications/rpm/rpm/123/')
        assert isinstance(result, RpmPublication)

    @patch('pulp3.Pulp3Client.post')
    @patch('pulp3.publications.get_task')
    def test_new_publication(self, mock_get_task, mock_post):
        """Tests when a new publication is created a Task obect is returned to monitor the creation
        """

        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        publication = RpmPublication(**{
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })

        result = new_publication(self.client, publication)

    @patch('pulp3.Pulp3Client.post')
    @patch('pulp3.publications.get_task')
    def test_new_publication_test_urls(self, mock_get_task, mock_post):
        """Tests when a new publication is created the correct url for publcation type is posted to
        """

        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'update-task',
            'logging_cid': '1234'
        })

        publication = RpmPublication(**{
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })
        result = new_publication(self.client, publication)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/publications/rpm/rpm/'

        publication = FilePublication(**{
            "repository_version": "/pulp/api/v3/repositories/file/file/456/versions/2/",
        })
        result = new_publication(self.client, publication)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/publications/file/file/'

        publication = DebPublication(**{
            "repository_version": "/pulp/api/v3/repositories/deb/apt/456/versions/2/",
        })
        result = new_publication(self.client, publication)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/publications/deb/apt/'

        publication = PythonPublication(**{
            "repository_version": "/pulp/api/v3/repositories/python/pypi/456/versions/2/",
        })
        result = new_publication(self.client, publication)
        post_args, post_kwargs = mock_post.call_args
        assert post_args[0] == '/publications/python/pypi/'

    @patch('pulp3.publications.new_publication')
    @patch('pulp3.publications.monitor_task')
    @patch('pulp3.publications.get_publication')
    def test_new_publication(self, mock_get_publication, mock_monitor_task, mock_new_publication):
        """Tests when a new publication is created a Task obect is returned to monitor the creation
        """

        mock_new_publication.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'new-publication-task',
            'logging_cid': '1234',
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'new-publication-task',
            'logging_cid': '1234',
            'created_resources': ['/pulp/api/v3/publications/rpm/rpm/123/']
        })

        mock_get_publication.return_value = RpmPublication(**{
            "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
            "date_created": datetime.now(),
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })

        publication = RpmPublication(**{
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })

        result = new_publication_monitor(self.client, publication)
        assert isinstance(publication, Publication)
        assert publication.pulp_href is not None

    @patch('pulp3.Pulp3Client.delete')
    @patch('pulp3.publications.get_task')
    def test_delete_publication(self, mock_get_task, mock_delete):
        """Tests that a task object is returned when publication deletion is requested
        """

        mock_delete.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-publication-task',
            'logging_cid': '1234',
        })

        publication = RpmPublication(**{
            "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
            "date_created": datetime.now(),
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })

        result = delete_publication(self.client, publication)
        assert isinstance(result, Task)

    @patch('pulp3.publications.delete_publication')
    @patch('pulp3.publications.monitor_task')
    def test_delete_publication_monitor(self, mock_monitor_task, mock_delete_publication):
        """Tests that a task object is returned when publication deletion completes successfully
        """

        mock_delete_publication.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-publication-task',
            'logging_cid': '1234',
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'delete-publication-task',
            'logging_cid': '1234',
        })

        publication = RpmPublication(**{
            "pulp_href": "/pulp/api/v3/publications/rpm/rpm/123/",
            "date_created": datetime.now(),
            "repository_version": "/pulp/api/v3/repositories/rpm/rpm/456/versions/2/",
            "metadata_checksum_type": "sha256",
            "package_checksum_type": "sha256",
            "gpgcheck": 1,
            "repo_gpgcheck": 0,
            "sqlite_metadata": False
        })

        result = delete_publication_monitor(self.client, publication)
        assert isinstance(result, Task)
        assert result.state == 'completed'

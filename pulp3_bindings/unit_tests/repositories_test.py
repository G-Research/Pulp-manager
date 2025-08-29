import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client, PulpV3InvalidArgumentError
from pulp3_bindings.pulp3.resources import (
    Task, Repository, FileRepository, RpmRepository, DebRepository, PythonRepository,
    ContainerRepository, FileRepositoryVersion, RpmRepositoryVersion,
    DebRepositoryVersion, PythonRepositoryVersion, ContainerRepositoryVersion
)
from pulp3_bindings.pulp3.repositories import (
    remove_invalid_creation_fields, get_repo_class, get_repo_version_class, get_all_repos,
    get_repo, get_all_repo_versions, get_repo_version, new_repo, update_repo,
    update_repo_monitor, modify_repo, modify_repo_monitor, sync_repo, sync_repo_monitor,
    delete_repo, delete_repo_monitor, copy_repo, copy_repo_monitor
)


class TestRepositories:
    """Tests forrepository api methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    def test_remove_invalid_creation_fields(self):
        """Checks that fields that shouldn't be in a post or patch are removed
        """

        repo = Repository(**{
            'pulp_href': '/some/url/',
            'pulp_created': datetime.now(),
            'versions_href': '/some/url/versions/',
            'pulp_labels': {},
            'latest_version_href': '/some/url/versions/1',
            'name': 'testing'
        })

        result = remove_invalid_creation_fields(repo)
        assert 'pulp_href' not in result
        assert 'pulp_created' not in result
        assert 'version_href' not in result
        assert 'latest_version_href' not in result

    def test_get_repo_class(self):
        """Checks the correct class is returned based on the type of repo being requested
        """

        assert get_repo_class('file') == FileRepository
        assert get_repo_class('rpm') == RpmRepository
        assert get_repo_class('deb') == DebRepository
        assert get_repo_class('python') == PythonRepository
        assert get_repo_class('container') == ContainerRepository

    def test_get_repo_class_fail(self):
        """Tests exception is raised when an unsupported type is passed for a repo class
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_repo_class('zippy')

    def test_get_repo_version_class(self):
        """Checks the correct class is returned based on the type of repo being requested
        """

        assert get_repo_version_class('file') == FileRepositoryVersion
        assert get_repo_version_class('rpm') == RpmRepositoryVersion
        assert get_repo_version_class('deb') == DebRepositoryVersion
        assert get_repo_version_class('python') == PythonRepositoryVersion
        assert get_repo_version_class('container') == ContainerRepositoryVersion

    def test_get_repo_version_class_fail(self):
        """Tests exception is raised when an unsupported type is passed for a repo class
        """

        with pytest.raises(PulpV3InvalidArgumentError):
            get_repo_version_class('zippy')

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repos(self, mock_get_page_results):
        """Tests that a list of Repository objects is returned
        """

        mock_get_page_results.return_value = [
            {
                'pulp_href': '/repositories/1/',
                'pulp_created': datetime.now(),
                'versions_href': '/repositories/1/versions/',
                'pulp_labels': {},
                'latest_version_href': '/repositories/1/versions/2/',
                'name': 'my repo',
                'description': None,
                'retain_repo_versions': None,
                'remote': None
            },
            {
                'pulp_href': '/repositories/2/',
                'pulp_created': datetime.now(),
                'versions_href': '/repositories/2/versions/',
                'pulp_labels': {},
                'latest_version_href': '/repositories/2/versions/2/',
                'name': 'my repo',
                'description': None,
                'retain_repo_versions': None,
                'remote': None
            }
        ]

        result = get_all_repos(self.client)
        get_page_results_args, get_page_results_kwargs = mock_get_page_results.call_args
        assert '/repositories/' in get_page_results_args[0]
        assert len(result) == 2
        assert isinstance(result[0], Repository)
        assert result[0].pulp_href == '/repositories/1/'
        assert result[1].pulp_href == '/repositories/2/'

    
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repos_types(self, mock_get_page_results):
        """Tests that limiting get_page_results to a type it returns
        the correct type of objects
        """

        # Reuse the base repos and then test instance of object matches
        # the class that was in the limit

        mock_get_page_results.return_value = [
            {
                'pulp_href': '/repositories/1/',
                'pulp_created': datetime.now(),
                'versions_href': '/repositories/1/versions/',
                'pulp_labels': {},
                'latest_version_href': '/repositories/1/versions/2/',
                'name': 'my repo',
                'description': None,
                'retain_repo_versions': None,
                'remote': None
            },
            {
                'pulp_href': '/repositories/2/',
                'pulp_created': datetime.now(),
                'versions_href': '/repositories/2/versions/',
                'pulp_labels': {},
                'latest_version_href': '/repositories/2/versions/2/',
                'name': 'my repo',
                'description': None,
                'retain_repo_versions': None,
                'remote': None
            }
        ]

        file_result = get_all_repos(self.client, 'file')
        rpm_result = get_all_repos(self.client, 'rpm')
        deb_result = get_all_repos(self.client, 'deb')
        python_result = get_all_repos(self.client, 'python')
        container_result = get_all_repos(self.client, 'container')

        assert isinstance(file_result[0], FileRepository)
        assert isinstance(rpm_result[0], RpmRepository)
        assert isinstance(deb_result[0], DebRepository)
        assert isinstance(python_result[0], PythonRepository)
        assert isinstance(container_result[0], ContainerRepository)

    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_file(self, mock_get):
        """Tests a FileRepository is returned when file in the repo href
        """

        mock_get.return_value =  {
            'pulp_href': '/pulp/api/v3/repositories/file/1',
            'pulp_created': datetime.now(),
            'versions_href': '/pulp/api/v3/repositories/file/1/versions/',
            'pulp_labels': {},
            'latest_version_href': '/pulp/api/v3/repositories/file/1/versions/2/',
            'name': 'my repo',
            'description': None,
            'retain_repo_versions': None,
            'remote': None
        }

        result = get_repo(self.client, '/pulp/api/v3/repositories/file/1')
        assert isinstance(result, FileRepository)

    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_rpm(self, mock_get):
        """Tests a RpmRepository is returned when rpm in the repo href
        """

        mock_get.return_value =  {
            'pulp_href': '/pulp/api/v3/repositories/rpm/1',
            'pulp_created': datetime.now(),
            'versions_href': '/pulp/api/v3/repositories/rpm/1/versions/',
            'pulp_labels': {},
            'latest_version_href': '/pulp/api/v3/repositories/rpm/1/versions/2/',
            'name': 'my repo',
            'description': None,
            'retain_repo_versions': None,
            'remote': None
        }

        result = get_repo(self.client, '/pulp/api/v3/repositories/rpm/1')
        assert isinstance(result, RpmRepository)

    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_deb(self, mock_get):
        """Tests a DebRepository is returned when deb in the repo href
        """

        mock_get.return_value =  {
            'pulp_href': '/pulp/api/v3/repositories/deb/1',
            'pulp_created': datetime.now(),
            'versions_href': '/pulp/api/v3/repositories/deb/1/versions/',
            'pulp_labels': {},
            'latest_version_href': '/pulp/api/v3/repositories/deb/1/versions/2/',
            'name': 'my repo',
            'description': None,
            'retain_repo_versions': None,
            'remote': None
        }

        result = get_repo(self.client, '/pulp/api/v3/repositories/deb/1')
        assert isinstance(result, DebRepository)

    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_python(self, mock_get):
        """Tests a DebRepository is returned when python in the repo href
        """

        mock_get.return_value =  {
            'pulp_href': '/pulp/api/v3/repositories/python/1',
            'pulp_created': datetime.now(),
            'versions_href': '/pulp/api/v3/repositories/python/1/versions/',
            'pulp_labels': {},
            'latest_version_href': '/pulp/api/v3/repositories/python/1/versions/2/',
            'name': 'my repo',
            'description': None,
            'retain_repo_versions': None,
            'remote': None
        }

        result = get_repo(self.client, '/pulp/api/v3/repositories/python/1')
        assert isinstance(result, PythonRepository)

    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_container(self, mock_get):
        """Tests a ContainerRepository is returned when container in the repo href
        """

        mock_get.return_value =  {
            'pulp_href': '/pulp/api/v3/repositories/container/1',
            'pulp_created': datetime.now(),
            'versions_href': '/pulp/api/v3/repositories/container/1/versions/',
            'pulp_labels': {},
            'latest_version_href': '/pulp/api/v3/repositories/container/1/versions/2/',
            'name': 'my repo',
            'description': None,
            'retain_repo_versions': None,
            'remote': None
        }

        result = get_repo(self.client, '/pulp/api/v3/repositories/container/1')
        assert isinstance(result, ContainerRepository)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.repositories.get_repo')
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repo_versions_rpm(self, mock_get_page_results, mock_get_repo):
        """Tests the correct repo type is returned for an RPM version
        """

        # No return value being set for mock_get_repo as only used to check a repo exists
        # return value etc are not inspected, as get_repo itself will fail if there are
        # errors

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/",
                "pulp_created": "2023-07-27T08:02:20.967935Z",
                "number": 1,
                "repository": "/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/",
                "base_version": None,
                "content_summary": {
                    "added": {
                        "rpm.distribution_tree": {
                            "count": 1,
                            "href": "/pulp/api/v3/content/rpm/distribution_trees/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        },
                        "rpm.package": {
                            "count": 417,
                            "href": "/pulp/api/v3/content/rpm/packages/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        },
                        "rpm.packagegroup": {
                            "count": 2,
                            "href": "/pulp/api/v3/content/rpm/packagegroups/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        }
                    },
                    "removed": {},
                    "present": {
                        "rpm.distribution_tree": {
                            "count": 1,
                            "href": "/pulp/api/v3/content/rpm/distribution_trees/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        },
                        "rpm.package": {
                            "count": 417,
                            "href": "/pulp/api/v3/content/rpm/packages/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        },
                        "rpm.packagegroup": {
                            "count": 2,
                            "href": "/pulp/api/v3/content/rpm/packagegroups/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                        }
                    }
                }
            }
        ]

        result = get_all_repo_versions(self.client, '/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/')
        assert isinstance(result[0], RpmRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.repositories.get_repo')
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repo_versions_deb(self, mock_get_page_results, mock_get_repo):
        """Tests the correct repo type is returned for an deb version
        """

        # No return value being set for mock_get_repo as only used to check a repo exists
        # return value etc are not inspected, as get_repo itself will fail if there are
        # errors
        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
                "pulp_created": "2023-07-27T08:02:20.967935Z",
                "number": 0,
                "repository": "/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/",
                "base_version": None,
                "content_summary": {
                    "added": {},
                    "removed": {},
                    "present": {}
                }
            }
        ]

        result = get_all_repo_versions(self.client, '/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/')
        assert isinstance(result[0], DebRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.repositories.get_repo')
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repo_versions_file(self, mock_get_page_results, mock_get_repo):
        """Tests the correct repo type is returned for an file version
        """

        # No return value being set for mock_get_repo as only used to check a repo exists
        # return value etc are not inspected, as get_repo itself will fail if there are
        # errors
        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
                "pulp_created": "2023-07-27T08:02:20.967935Z",
                "number": 0,
                "repository": "/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/",
                "base_version": None,
                "content_summary": {
                    "added": {},
                    "removed": {},
                    "present": {}
                }
            }
        ]

        result = get_all_repo_versions(self.client, '/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/')
        assert isinstance(result[0], FileRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.repositories.get_repo')
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repo_versions_python(self, mock_get_page_results, mock_get_repo):
        """Tests the correct repo type is returned for an python version
        """

        # No return value being set for mock_get_repo as only used to check a repo exists
        # return value etc are not inspected, as get_repo itself will fail if there are
        # errors
        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
                "pulp_created": "2023-07-27T08:02:20.967935Z",
                "number": 0,
                "repository": "/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/",
                "base_version": None,
                "content_summary": {
                    "added": {},
                    "removed": {},
                    "present": {}
                }
            }
        ]

        result = get_all_repo_versions(self.client, '/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/')
        assert isinstance(result[0], PythonRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.repositories.get_repo')
    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_repo_versions_container(self, mock_get_page_results, mock_get_repo):
        """Tests the correct repo type is returned for an container version
        """

        # No return value being set for mock_get_repo as only used to check a repo exists
        # return value etc are not inspected, as get_repo itself will fail if there are
        # errors
        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
                "pulp_created": "2023-07-27T08:02:20.967935Z",
                "number": 0,
                "repository": "/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/",
                "base_version": None,
                "content_summary": {
                    "added": {},
                    "removed": {},
                    "present": {}
                }
            }
        ]

        result = get_all_repo_versions(self.client, '/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/')
        assert isinstance(result[0], ContainerRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_version_rpm(self, mock_get):
        """Tests the correct repo type is returned for an RPM version
        """

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/",
            "pulp_created": "2023-07-27T08:02:20.967935Z",
            "number": 1,
            "repository": "/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/",
            "base_version": None,
            "content_summary": {
                "added": {
                    "rpm.distribution_tree": {
                        "count": 1,
                        "href": "/pulp/api/v3/content/rpm/distribution_trees/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    },
                    "rpm.package": {
                        "count": 417,
                        "href": "/pulp/api/v3/content/rpm/packages/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    },
                    "rpm.packagegroup": {
                        "count": 2,
                        "href": "/pulp/api/v3/content/rpm/packagegroups/?repository_version_added=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    }
                },
                "removed": {},
                "present": {
                    "rpm.distribution_tree": {
                        "count": 1,
                        "href": "/pulp/api/v3/content/rpm/distribution_trees/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    },
                    "rpm.package": {
                        "count": 417,
                        "href": "/pulp/api/v3/content/rpm/packages/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    },
                    "rpm.packagegroup": {
                        "count": 2,
                        "href": "/pulp/api/v3/content/rpm/packagegroups/?repository_version=/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/versions/1/"
                    }
                }
            }
        }

        result = get_repo_version(self.client, '/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/1/')
        assert isinstance(result, RpmRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_version_deb(self, mock_get):
        """Tests the correct repo type is returned for an deb version
        """

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
            "pulp_created": "2023-07-27T08:02:20.967935Z",
            "number": 1,
            "repository": "/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/",
            "base_version": None,
            "content_summary": {
                "added": {},
                "removed": {},
                "present": {}
            }
        }

        result = get_repo_version(self.client, '/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/0/')
        assert isinstance(result, DebRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_version_file(self, mock_get):
        """Tests the correct repo type is returned for an file version
        """

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
            "pulp_created": "2023-07-27T08:02:20.967935Z",
            "number": 1,
            "repository": "/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/",
            "base_version": None,
            "content_summary": {
                "added": {},
                "removed": {},
                "present": {}
            }
        }

        result = get_repo_version(self.client, '/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/0/')
        assert isinstance(result, FileRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_version_python(self, mock_get):
        """Tests the correct repo type is returned for an python version
        """

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
            "pulp_created": "2023-07-27T08:02:20.967935Z",
            "number": 1,
            "repository": "/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/",
            "base_version": None,
            "content_summary": {
                "added": {},
                "removed": {},
                "present": {}
            }
        }

        result = get_repo_version(self.client, '/pulp/api/v3/repositories/python/python/0189965d-8010-7072-a003-94fedbddb0de/0/')
        assert isinstance(result, PythonRepositoryVersion)

    # Tests for repo versions are done on each specific repo type, because
    # there is no generic list option
    @patch('pulp3.Pulp3Client.get')
    def test_get_repo_version_container(self, mock_get):
        """Tests the correct repo type is returned for an container version
        """

        # Used one real value for RPM to make sure the Pydantic representation works correctly
        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/versions/0/",
            "pulp_created": "2023-07-27T08:02:20.967935Z",
            "number": 1,
            "repository": "/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/",
            "base_version": None,
            "content_summary": {
                "added": {},
                "removed": {},
                "present": {}
            }
        }

        result = get_repo_version(self.client, '/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/0/')
        assert isinstance(result, ContainerRepositoryVersion)

    @patch('pulp3.Pulp3Client.post')
    def test_new_repo_file(self, mock_post):
        """Tests that when a new file repo is created, the properties are updates for
        the object that was passed through
        """

        mock_pulp_href = "/pulp/api/v3/repositories/file/file/0189965d-8010-7072-a003-94fedbddb0de/"
        mock_post.return_value = {
            "pulp_href": mock_pulp_href,
            "name": "Test-Repo"
        }

        repo = FileRepository(**{"name": "Test-Repo"})
        new_repo(self.client, repo)
        assert repo.pulp_href == mock_pulp_href

    @patch('pulp3.Pulp3Client.post')
    def test_new_repo_rpm(self, mock_post):
        """Tests that when a new rpm repo is created, the properties are updates for
        the object that was passed through
        """

        mock_pulp_href = "/pulp/api/v3/repositories/rpm/rpm/0189965d-8010-7072-a003-94fedbddb0de/"
        mock_post.return_value = {
            "pulp_href": mock_pulp_href,
            "name": "Test-Repo"
        }

        repo = RpmRepository(**{"name": "Test-Repo"})
        new_repo(self.client, repo)
        assert repo.pulp_href == mock_pulp_href

    @patch('pulp3.Pulp3Client.post')
    def test_new_repo_deb(self, mock_post):
        """Tests that when a new deb repo is created, the properties are updates for
        the object that was passed through
        """

        mock_pulp_href = "/pulp/api/v3/repositories/deb/deb/0189965d-8010-7072-a003-94fedbddb0de/"
        mock_post.return_value = {
            "pulp_href": mock_pulp_href,
            "name": "Test-Repo"
        }

        repo = DebRepository(**{"name": "Test-Repo"})
        new_repo(self.client, repo)
        assert repo.pulp_href == mock_pulp_href

    @patch('pulp3.Pulp3Client.post')
    def test_new_repo_python(self, mock_post):
        """Tests that when a new file repo is created, the properties are updates for
        the object that was passed through
        """

        mock_pulp_href = "/pulp/api/v3/repositories/python/pthon/0189965d-8010-7072-a003-94fedbddb0de/"
        mock_post.return_value = {
            "pulp_href": mock_pulp_href,
            "name": "Test-Repo"
        }

        repo = PythonRepository(**{"name": "Test-Repo"})
        new_repo(self.client, repo)
        assert repo.pulp_href == mock_pulp_href

    @patch('pulp3.Pulp3Client.post')
    def test_new_repo_container(self, mock_post):
        """Tests that when a new container repo is created, the properties are updates for
        the object that was passed through
        """

        mock_pulp_href = "/pulp/api/v3/repositories/container/container/0189965d-8010-7072-a003-94fedbddb0de/"
        mock_post.return_value = {
            "pulp_href": mock_pulp_href,
            "name": "Test-Repo"
        }

        repo = ContainerRepository(**{"name": "Test-Repo"})
        new_repo(self.client, repo)
        assert repo.pulp_href == mock_pulp_href

    @patch('pulp3.repositories.get_task')
    @patch('pulp3.Pulp3Client.patch')
    def test_update_repo(self, mock_patch, mock_get_task):
        """Tests that when a repo is updated, a task object is returned that can
        be used for monitoring
        """

        mock_task_href = '/pulp/api/v3/tasks/123'
        mock_patch.return_value = {'task': mock_task_href}
        mock_get_task.return_value = Task(**{
            'pulp_href': mock_task_href,
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'sync-task',
            'logging_cid': '1234'
        })
        repo = RpmRepository(**{'name': 'Test-Repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'})
        result = update_repo(self.client, repo)

        assert isinstance(result, Task)
        assert result.pulp_href == mock_task_href

    @patch('pulp3.repositories.update_repo')
    @patch('pulp3.repositories.monitor_task')
    @patch('pulp3.repositories.get_repo')
    def test_update_repo_monitor(self, mock_get_repo, mock_monitor_task, mock_update_repo):
        """Tests that the repo object is updated
        """

        # No retuurn value set for mock_monitor_task as result not checked
        mock_update_repo.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'sync-task',
            'logging_cid': '1234'
        })
        mock_get_repo.return_value = RpmRepository(
            **{'name': 'test-repo-updated', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        repo = RpmRepository(**{'name': 'test-repo'})
        update_repo_monitor(self.client, repo)
        assert repo.name == 'test-repo-updated'

    @patch('pulp3.repositories.get_task')
    @patch('pulp3.Pulp3Client.post')
    def test_copy_repo_rpm(self, mock_post, mock_get_task):
        """Tests what when a copy is kicked off, for an rpm correct arguments are
        passed and a task object is returned
        """

        mock_task_href = '/pulp/api/v3/tasks/123'
        mock_post.return_value = {'task': mock_task_href}
        mock_get_task.return_value = Task(**{
            'pulp_href': mock_task_href,
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'copy-task',
            'logging_cid': '1234'
        })

        source_repo = RpmRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'source_repo',
            'latest_version_href': '/pulp/api/v3/repositories/rpm/rpm/123/versions/1/'
        })

        dest_repo = RpmRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/456/',
            'pulp_created': datetime.now(),
            'name': 'dest_repo'
        })

        result = copy_repo(self.client, source_repo, dest_repo)

        # mock_post_args is a tuple that we index into
        mock_post_args, mock_post_kwargs = mock_post.call_args
        assert mock_post_args[0] == '/rpm/copy/'
        assert mock_post_args[1]['config'][0]['source_repo_version'] == '/pulp/api/v3/repositories/rpm/rpm/123/versions/1/'
        assert mock_post_args[1]['config'][0]['dest_repo'] == '/pulp/api/v3/repositories/rpm/rpm/456/'
        # structured only supported on debs
        assert 'structured' not in mock_post_args[1]
        assert isinstance(result, Task)

    @patch('pulp3.repositories.get_task')
    @patch('pulp3.Pulp3Client.post')
    def test_copy_repo_deb(self, mock_post, mock_get_task):
        """Tests what when a copy is kicked off, for an deb correct arguments are
        passed and a task object is returned
        """

        mock_task_href = '/pulp/api/v3/tasks/123'
        mock_post.return_value = {'task': mock_task_href}
        mock_get_task.return_value = Task(**{
            'pulp_href': mock_task_href,
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'copy-task',
            'logging_cid': '1234'
        })

        source_repo = DebRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/deb/apt/123/',
            'pulp_created': datetime.now(),
            'name': 'source_repo',
            'latest_version_href': '/pulp/api/v3/repositories/deb/apt/123/versions/1/'
        })

        dest_repo = DebRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/deb/apt/456/',
            'pulp_created': datetime.now(),
            'name': 'dest_repo'
        })

        result = copy_repo(self.client, source_repo, dest_repo)

        # mock_post_args is a tuple that we index into
        mock_post_args, mock_post_kwargs = mock_post.call_args
        assert mock_post_args[0] == '/deb/copy/'
        assert mock_post_args[1]['config'][0]['source_repo_version'] == '/pulp/api/v3/repositories/deb/apt/123/versions/1/'
        assert mock_post_args[1]['config'][0]['dest_repo'] == '/pulp/api/v3/repositories/deb/apt/456/'
        assert 'structured' in mock_post_args[1]
        assert isinstance(result, Task)

    def test_copy_repo_source_dest_mismatch(self):
        """Tests mismtach source, dest repo types raises PulpV3InvalidArgumentError
        """

        source_repo = RpmRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'source_repo',
            'latest_version_href': '/pulp/api/v3/repositories/rpm/rpm/123/versions/1/'
        })

        dest_repo = DebRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/deb/apt/456/',
            'pulp_created': datetime.now(),
            'name': 'dest_repo'
        })

        with pytest.raises(PulpV3InvalidArgumentError):
            copy_repo(self.client, source_repo, dest_repo)

    def test_copy_repo_invalid_type(self):
        """Tests unsupported repo type, raises PulpV3InvalidArgumentError
        """

        source_repo = FileRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/file/file/123/',
            'pulp_created': datetime.now(),
            'name': 'source_repo',
            'latest_version_href': '/pulp/api/v3/repositories/file/file/123/versions/1/'
        })

        dest_repo = FileRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/file/file/456/',
            'pulp_created': datetime.now(),
            'name': 'dest_repo'
        })

        with pytest.raises(PulpV3InvalidArgumentError):
            copy_repo(self.client, source_repo, dest_repo)

    @patch('pulp3.repositories.monitor_task')
    @patch('pulp3.repositories.copy_repo')
    def test_copy_repo_monitor(self, mock_copy_repo, mock_monitor_task):
        """Tests what when a copy is kicked off, it is watched to completion
        """

        mock_task_href = '/pulp/api/v3/tasks/123'
        mock_copy_repo.return_value = Task(**{
            'pulp_href': mock_task_href,
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'copy-task',
            'logging_cid': '1234'
        })
        mock_monitor_task.return_value = Task(**{
            'pulp_href': mock_task_href,
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'copy-task',
            'logging_cid': '1234'
        })

        source_repo = RpmRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123/',
            'pulp_created': datetime.now(),
            'name': 'source_repo',
            'latest_version_href': '/pulp/api/v3/repositories/rpm/rpm/123/versions/1/'
        })

        dest_repo = RpmRepository(**{
            'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/456/',
            'pulp_created': datetime.now(),
            'name': 'dest_repo'
        })

        result = copy_repo_monitor(self.client, source_repo, dest_repo)
        assert isinstance(result, Task)

    def test_modify_repo_invalid_type(self):
        """Tests that when modify is called on an unsupported repo type
        PulpV3InvalidArgumentError
        """

        repo = ContainerRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/container/container/123'}
        )

        with pytest.raises(PulpV3InvalidArgumentError):
            modify_repo(self.client, repo, '/pulp/api/v3/repositories/container/container/123/version/1')

    def test_modify_repo_no_content_units(self):
        """Tests that PulpV3InvalidArgumentError is raised is no content units to add or remove
        are specified
        """

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        with pytest.raises(PulpV3InvalidArgumentError):
            modify_repo(self.client, repo, '/pulp/api/v3/repositories/rpm/rpm/123/version/1')


    @patch('pulp3.repositories.get_task')
    @patch('pulp3.Pulp3Client.post')
    def test_modify_repo(self, mock_post, mock_get_task):
        """Tests that when modify repo is called with correct arguments a task object is returned
        """

        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'modify-task',
            'logging_cid': '1234'
        })

        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result =  modify_repo(
            self.client,
            repo,
            '/pulp/api/v3/repositories/rpm/rpm/123/version/1/',
            ['/pulp/content/to/add'],
            ['/pulp/content/to/remove']
        )

        post_args, post_kwargs = mock_post.call_args
        post_url = post_args[0]
        post_body = post_args[1]

        assert post_url == '/pulp/api/v3/repositories/rpm/rpm/123/modify/'
        assert post_body['base_version'] == '/pulp/api/v3/repositories/rpm/rpm/123/version/1/'
        assert post_body['add_content_units'][0] == '/pulp/content/to/add'
        assert post_body['remove_content_units'][0] == '/pulp/content/to/remove'
        assert isinstance(result, Task)

    @patch('pulp3.repositories.modify_repo')
    @patch('pulp3.repositories.monitor_task')
    def test_modify_repo_monitor(self, mock_monitor_task, mock_modify_repo):
        """Tests that when modify repo monitor completes successfully a task object is returned
        """

        mock_modify_repo.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'modify-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'modify-task',
            'logging_cid': '1234'
        })


        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result = modify_repo_monitor(
            self.client,
            repo,
            '/pulp/api/v3/repositories/rpm/rpm/123/version/1/',
            ['/pulp/content/to/add'],
            ['/pulp/content/to/remove']
        )

        assert isinstance(result, Task)
        assert result.state == 'completed'

    @patch('pulp3.repositories.get_task')
    @patch('pulp3.Pulp3Client.post')
    def test_sync_repo(self, mock_post, mock_get_task):
        """Tests that when sync repo is called a Task object is returned for tracking progress 
        """

        mock_post.return_value = {'task': '/pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'sync-task',
            'logging_cid': '1234'
        })

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result = sync_repo(self.client, repo, {})
        post_args, post_kwargs = mock_post.call_args

        assert post_args[0] == '/pulp/api/v3/repositories/rpm/rpm/123/sync/'
        assert post_args[1] == {}
        assert isinstance(result, Task)

    @patch('pulp3.repositories.sync_repo')
    @patch('pulp3.repositories.monitor_task')
    def test_modify_repo_monitor(self, mock_monitor_task, mock_sync_repo):
        """Tests that when sync repo monitor completes successfully a task object is returned
        """

        mock_sync_repo.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'sync-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'sync-task',
            'logging_cid': '1234'
        })

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result = sync_repo_monitor(self.client, repo, {})
        assert isinstance(result, Task)
        assert result.state == 'completed'

    @patch('pulp3.Pulp3Client.delete')
    @patch('pulp3.repositories.get_task')
    def test_delete_repo(self, mock_get_task, mock_delete):
        """Tests that when delete is called on a repo a task object is returned
        """

        mock_delete.return_value = {'task': 'pulp/api/v3/tasks/123'}
        mock_get_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-task',
            'logging_cid': '1234'
        })

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result = delete_repo(self.client, repo)
        assert isinstance(result, Task)

    @patch('pulp3.repositories.delete_repo')
    @patch('pulp3.repositories.monitor_task')
    def test_delete_repo_monitor(self, mock_monitor_task, mock_delete_repo):
        """Tests that when delete repo monitor finishes to completeion task object is returned
        """
        mock_delete_repo.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'running',
            'name': 'delete-task',
            'logging_cid': '1234'
        })

        mock_monitor_task.return_value = Task(**{
            'pulp_href': '/pulp/api/v3/tasks/123',
            'pulp_created': datetime.now(),
            'state': 'completed',
            'name': 'delete-task',
            'logging_cid': '1234'
        })

        repo = RpmRepository(
            **{'name': 'test-repo', 'pulp_href': '/pulp/api/v3/repositories/rpm/rpm/123'}
        )

        result = delete_repo_monitor(self.client, repo)
        assert isinstance(result, Task)
        assert result.state == 'completed'

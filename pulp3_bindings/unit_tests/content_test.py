import pytest
from pytest_mock import mocker
from datetime import datetime

import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client
from pulp3_bindings.pulp3.content import (
    get_content_package_class, get_all_content, get_all_content_packages, get_content_package
)
from pulp3_bindings.pulp3.resources import (
    Content, RpmPackageContent, FilePackageContent, DebPackageContent, PythonPackageContent
)


class TestContent:
    """Tests for content API methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    def test_get_content_package_class(self):
        """Tests the correct content package is returned given the specified type
        """

        assert get_content_package_class('file') == FilePackageContent
        assert get_content_package_class('rpm') == RpmPackageContent
        assert get_content_package_class('deb') == DebPackageContent
        assert get_content_package_class('python') == PythonPackageContent

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_content(self, mock_get_page_results):
        """Tests that a list of type content is returned
        """

        mock_get_page_results.return_value = [
             {
                "pulp_href": "/pulp/api/v3/content/rpm/packages/018a0353-39e4-75cd-90f0-45ab2835dd93/",
                "pulp_created": "2023-08-17T11:48:39.589453Z",
                "artifacts": {
                    "python2-vine-1.1.3-5.el7.noarch.rpm": "/pulp/api/v3/artifacts/018a0353-79ec-7ba5-bb68-0fefdfa6ca40/"
                }
            },
            {
                "pulp_href": "/pulp/api/v3/content/rpm/packages/018a0353-39e2-741c-8cf5-2fc9c76bcaef/",
                "pulp_created": "2023-08-17T11:48:39.587580Z",
                "artifacts": {
                    "python2-solv-0.7.3-4.el7.x86_64.rpm": "/pulp/api/v3/artifacts/018a0353-79e7-7a30-89fd-d535609be17d/"
                }
            }
        ]

        result = get_all_content(self.client)
        assert len(result) == 2
        assert isinstance(result[0], Content)

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_content_packages(self, mock_get_page_results):
        """Tests that a list of specified content packages is returned
        """

        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/content/rpm/packages/018a0353-39e4-75cd-90f0-45ab2835dd93/",
                "pulp_created": "2023-08-17T11:48:39.589453Z",
                "md5": None,
                "sha1": None,
                "sha224": "d68106da92ba42fb47de031d53763bbee069b2fe6bbc29f69ef0eb9b",
                "sha256": "144f8c25a155630031885efb1d0cb54bcf463d22469a06bde0d3e0c550bd6cc8",
                "sha384": "4c9ab8038359cd3c269cae173e32cb12d9bf7e5aa3543d0617be51f3715f59e80bed5ecd714d816cad1a8cc31f5e86ad",
                "sha512": "58c485cbf7defe99b96c1f9b9ec839a86bff3ffce1bba66637c2a6f83944e3774125d8cf078632538daf6602dd1508f27853454a242b197d2942b59e3449899a",
                "artifact": "/pulp/api/v3/artifacts/018a0353-79ec-7ba5-bb68-0fefdfa6ca40/",
                "name": "python2-vine",
                "epoch": "10",
                "version": "1.1.3",
                "release": "5.el7",
                "arch": "noarch",
                "pkgId": "144f8c25a155630031885efb1d0cb54bcf463d22469a06bde0d3e0c550bd6cc8",
                "checksum_type": "sha256",
                "summary": "Promises, promises, promises",
                "description": "Promises, promises, promises",
                "url": "http://github.com/celery/vine",
                "changelogs": [
                    [
                        "Matthias Runge <mrunge@redhat.com> - 1.1.3-1",
                        1482840000,
                        "- Initial package. (rhbz#1408869)"
                    ]
                ],
                "files": [
                    [
                        None,
                        "/usr/lib/python2.7/site-packages/vine-1.1.3-py2.7.egg-info/",
                        "PKG-INFO"
                    ]
                ],
                "requires": [
                    [
                        "python(abi)",
                        "EQ",
                        "0",
                        "2.7",
                        None,
                        False
                    ]
                ],
                "provides": [
                    [
                        "python-vine",
                        None,
                        None,
                        None,
                        None,
                        False
                    ],
                    [
                        "python2-vine",
                        "EQ",
                        "10",
                        "1.1.3",
                        "5.el7",
                        False
                    ]
                ],
                "conflicts": [],
                "obsoletes": [
                    [
                        "python-vine",
                        "LT",
                        "0",
                        "1.1.3",
                        None,
                        False
                    ]
                ],
                "suggests": [],
                "enhances": [],
                "recommends": [],
                "supplements": [],
                "location_base": "",
                "location_href": "python2-vine-1.1.3-5.el7.noarch.rpm",
                "rpm_buildhost": "koji.katello.org",
                "rpm_group": "Unspecified",
                "rpm_license": "BSD",
                "rpm_packager": "Koji",
                "rpm_sourcerpm": "python-vine-1.1.3-5.el7.src.rpm",
                "rpm_vendor": "Koji",
                "rpm_header_start": 976,
                "rpm_header_end": 7908,
                "is_modular": False,
                "size_archive": 81680,
                "size_installed": 76056,
                "size_package": 26540,
                "time_build": 1550864393,
                "time_file": 1550865528
            }
        ]

        result = get_all_content_packages(self.client, 'rpm')
        assert isinstance(result[0], RpmPackageContent)

    @patch('pulp3.Pulp3Client.get')
    def test_get_content_package(self, mock_get):
        """Tests that the requested content packages is returned
        """

        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/content/rpm/packages/018a0353-39e4-75cd-90f0-45ab2835dd93/",
            "pulp_created": "2023-08-17T11:48:39.589453Z",
            "md5": None,
            "sha1": None,
            "sha224": "d68106da92ba42fb47de031d53763bbee069b2fe6bbc29f69ef0eb9b",
            "sha256": "144f8c25a155630031885efb1d0cb54bcf463d22469a06bde0d3e0c550bd6cc8",
            "sha384": "4c9ab8038359cd3c269cae173e32cb12d9bf7e5aa3543d0617be51f3715f59e80bed5ecd714d816cad1a8cc31f5e86ad",
            "sha512": "58c485cbf7defe99b96c1f9b9ec839a86bff3ffce1bba66637c2a6f83944e3774125d8cf078632538daf6602dd1508f27853454a242b197d2942b59e3449899a",
            "artifact": "/pulp/api/v3/artifacts/018a0353-79ec-7ba5-bb68-0fefdfa6ca40/",
            "name": "python2-vine",
            "epoch": "10",
            "version": "1.1.3",
            "release": "5.el7",
            "arch": "noarch",
            "pkgId": "144f8c25a155630031885efb1d0cb54bcf463d22469a06bde0d3e0c550bd6cc8",
            "checksum_type": "sha256",
            "summary": "Promises, promises, promises",
            "description": "Promises, promises, promises",
            "url": "http://github.com/celery/vine",
            "changelogs": [
                [
                    "Matthias Runge <mrunge@redhat.com> - 1.1.3-1",
                    1482840000,
                    "- Initial package. (rhbz#1408869)"
                ]
            ],
            "files": [
                [
                    None,
                    "/usr/lib/python2.7/site-packages/vine-1.1.3-py2.7.egg-info/",
                    "PKG-INFO"
                ]
            ],
            "requires": [
                [
                    "python(abi)",
                    "EQ",
                    "0",
                    "2.7",
                    None,
                    False
                ]
            ],
            "provides": [
                [
                    "python-vine",
                    None,
                    None,
                    None,
                    None,
                    False
                ],
                [
                    "python2-vine",
                    "EQ",
                    "10",
                    "1.1.3",
                    "5.el7",
                    False
                ]
            ],
            "conflicts": [],
            "obsoletes": [
                [
                    "python-vine",
                    "LT",
                    "0",
                    "1.1.3",
                    None,
                    False
                ]
            ],
            "suggests": [],
            "enhances": [],
            "recommends": [],
            "supplements": [],
            "location_base": "",
            "location_href": "python2-vine-1.1.3-5.el7.noarch.rpm",
            "rpm_buildhost": "koji.katello.org",
            "rpm_group": "Unspecified",
            "rpm_license": "BSD",
            "rpm_packager": "Koji",
            "rpm_sourcerpm": "python-vine-1.1.3-5.el7.src.rpm",
            "rpm_vendor": "Koji",
            "rpm_header_start": 976,
            "rpm_header_end": 7908,
            "is_modular": False,
            "size_archive": 81680,
            "size_installed": 76056,
            "size_package": 26540,
            "time_build": 1550864393,
            "time_file": 1550865528
        }

        result = get_content_package(self.client, '/pulp/api/v3/content/rpm/packages/018a0353-39e4-75cd-90f0-45ab2835dd93/')
        assert isinstance(result, RpmPackageContent)

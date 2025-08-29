import json
import pytest
from pytest_mock import mocker
from datetime import datetime
from mock import patch

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client
from pulp3_bindings.pulp3.signing_services import get_all_signing_services, get_signing_service
from pulp3_bindings.pulp3.resources import SigningService

class TestSigningServices:
    """Tests for content API methods
    """

    def setup_method(self, test_method):
    	"""Sets up all test methods so that a pulp client
    	is available

    	:param test_method: pytest test_method to setup
    	"""

    	self.pulp_address = 'pulp.domain'
    	self.client = Pulp3Client(self.pulp_address, 'username', 'pass')

    @patch('pulp3.Pulp3Client.get_page_results')
    def test_get_all_signing_services(self, mock_get_page_results):
        """Tests that a list of type SigningService is returned
        """

        mock_get_page_results.return_value = [
            {
                "pulp_href": "/pulp/api/v3/signing-services/018a8df9-02fd-74ef-8eda-05a8e75e42a1/",
                "pulp_created": "2023-09-13T09:57:02.262258Z",
                "name": "pulp_deb",
                "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----",
                "pubkey_fingerprint": "1B1F8B15A",
                "script": "/usr/local/bin/sign_deb_release.sh"
            }
        ]

        result = get_all_signing_services(self.client)
        assert len(result) == 1
        assert isinstance(result[0], SigningService)

    @patch('pulp3.Pulp3Client.get')
    def test_get_signing_service(self, mock_get):
        """Tests that the requested signing service is returned
        """

        mock_get.return_value = {
            "pulp_href": "/pulp/api/v3/signing-services/018a8df9-02fd-74ef-8eda-05a8e75e42a1/",
            "pulp_created": "2023-09-13T09:57:02.262258Z",
            "name": "pulp_deb",
            "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----",
            "pubkey_fingerprint": "1B1F8B15A",
            "script": "/usr/local/bin/sign_deb_release.sh"
        }

        result = get_signing_service(self.client, '/pulp/api/v3/signing-services/018a8df9-02fd-74ef-8eda-05a8e75e42a1/')
        assert isinstance(result, SigningService)

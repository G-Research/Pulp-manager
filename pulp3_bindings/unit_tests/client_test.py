import pytest
from pytest_mock import mocker
import json

from mock import patch
from .mock_http_methods import MockResponse

from sys import path
path.append('.')
from pulp3_bindings.pulp3 import Pulp3Client, PulpV3APIError


request_count = 0

def mock_request_method_vault(*args, **kwargs):
    """mock request method for vault agent testing
    """

    global request_count
    if request_count == 0:
        request_count += 1
        return MockResponse(401, 'Auth error')
    return MockResponse(200, 'OK')



class TestPulp3Client:
    """Class of tests for Pulp3 Client
    """

    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def setup_method(self, test_method, mock_get_svc_accont_password):
        """Sets up all test methods so that a pulp client
        is available

        :param test_method: pytest test_method to setup
        """

        mock_get_svc_account_password = 'password_from_vault'
        self.pulp_address = 'pulp.domain'
        self.client = Pulp3Client(self.pulp_address, 'username', 'pass')
        self.vault_agent_client = Pulp3Client(self.pulp_address, 'username', use_vault_agent=True)

    def test_base_url(self):
        """Tests that the _base_url has been set correctly when the object
        is constructed
        """

        assert self.client._base_url == 'https://{0}/pulp/api/v3'.format(self.pulp_address)

    def test_format_href(self):
        """Tests that _formt_href strips the appropriate part of the base url
        """

        assert self.client._format_href('/pulp/api/v3/test/') == '/test/'
        assert self.client._format_href('/test/') == '/test/'

    def test_request_error_handler_ok(self):
        """Test that when a good status code is given the error handler
        doesn't raise an exception
        """

        response = MockResponse(200, 'OK')
        self.client._request_error_handler('GET', response, '/fake/url')

    def test_request_error_handler_expect_fail(self):
        """Tests that when an error HTTP status is returned PulpV3APIError is raised
        """

        response = MockResponse(400, 'Failure')
        with pytest.raises(PulpV3APIError):
            self.client._request_error_handler('GET', response, '/fake/url')

    @patch('requests.get', return_value=MockResponse(200, 'OK'))
    def test_get_ok(self, mock_requests_get):
        """Tests that get method doesn't raise any errors when a request is fine
        """

        self.client.get('/fake/url/')

    @patch('requests.get', return_value=MockResponse(200, 'OK'))
    def test_get_ok_args(self, mock_requests_get):
        """Tests that get method doesn't raise any errors when a request is fine
        """

        self.client.get('/fake/url/', params={"param1": "value1", "param_list": [1, 2, 3]})
        call_args, call_kwargs = mock_requests_get.call_args
        assert "param1=value1" in call_args[0]
        assert "&param_list=1&param_list=2&param_list=3" in call_args[0]

    @patch('requests.get', return_value=MockResponse(400, 'OK'))
    def test_get_fail(self, mock_requests_get):
        """Tests that get raises PulpV3APIError when failure HTTP code is returned
        """

        with pytest.raises(PulpV3APIError):
            self.client.get('/fake/url/')

    @patch('requests.get')
    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def test_get_vault_agent(self, mock_get_svc_account_password, mock_requests_get):
        """Tests that when first reponse on a get is a 401, vault credentials are 
        re-retrieved and HTTP get request is made again
        """

        global request_count
        request_count = 0
        mock_get_svc_account_password.return_value = 'password'

        mock_requests_get.side_effect = mock_request_method_vault
        self.vault_agent_client.get('/fake/url/')
        assert mock_get_svc_account_password.call_count == 1

    @patch('requests.get')
    def test_get_page_results(self, mock_get_requests):
        """Test that get_page_results retrieves all object from a set of paginated results
        """

        response1 = MockResponse(
            status_code=200,
            text='OK',
            json_output={
                'next': '/some/fake/url/?page=1',
                'results': [1]
            }
        )
        response2 = MockResponse(
            status_code=200,
            text='OK',
            json_output={
                'next': None,
                'results': [2]
            }
        )

        responses = [response1, response2]

        # Create a side effect for the mock get, and just populate
        # it with the number of args that we are calling get with
        def get_response(url, auth, headers, verify):
            return responses.pop(0)

        mock_get_requests.side_effect = get_response
        result = self.client.get_page_results('/fake/url')
        print(result)
        assert result[0] == 1
        assert result[1] == 2


    @patch('requests.post', return_value=MockResponse(200, 'OK'))
    def test_post_ok(self, mock_requests_post):
        """Tests that when post doesn't raise any errors when a request is fine
        """

        self.client.post('/fake/url/')

    @patch('requests.post', return_value=MockResponse(400, 'OK'))
    def test_post_fail(self, mock_requests_post):
        """Tests that when post raises PulpV3APIError when failure HTTP code is returned
        """

        with pytest.raises(PulpV3APIError):
            self.client.post('/fake/url/')

    @patch('requests.post')
    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def test_post_vault_agent(self, mock_get_svc_account_password, mock_requests_post):
        """Tests that when first reponse on a post is a 401, vault credentials are 
        re-retrieved and HTTP post request is made again
        """

        global request_count
        request_count = 0
        mock_get_svc_account_password.return_value = 'password'

        mock_requests_post.side_effect = mock_request_method_vault
        self.vault_agent_client.post('/fake/url/')
        assert mock_get_svc_account_password.call_count == 1

    @patch('requests.patch', return_value=MockResponse(200, 'OK'))
    def test_patch_ok(self, mock_requests_patch):
        """Tests that when patch doesn't raise any errors when a request is fine
        """

        self.client.patch('/fake/url/', {})

    @patch('requests.patch', return_value=MockResponse(400, 'OK'))
    def test_patch_fail(self, mock_requests_patch):
        """Tests that when patch raises PulpV3APIError when failure HTTP code is returned
        """

        with pytest.raises(PulpV3APIError):
            self.client.patch('/fake/url/', {})

    @patch('requests.patch')
    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def test_patch_vault_agent(self, mock_get_svc_account_password, mock_requests_patch):
        """Tests that when first reponse on a patch is a 401, vault credentials are 
        re-retrieved and HTTP patch request is made again
        """

        global request_count
        request_count = 0
        mock_get_svc_account_password.return_value = 'password'

        mock_requests_patch.side_effect = mock_request_method_vault
        self.vault_agent_client.patch('/fake/url/', {})
        assert mock_get_svc_account_password.call_count == 1

    @patch('requests.put', return_value=MockResponse(200, 'OK'))
    def test_put_ok(self, mock_requests_put):
        """Tests that when put doesn't raise any errors when a request is fine
        """

        self.client.put('/fake/url/', {})

    @patch('requests.put', return_value=MockResponse(400, 'OK'))
    def test_put_fail(self, mock_requests_put):
        """Tests that when put raises PulpV3APIError when failure HTTP code is returned
        """

        with pytest.raises(PulpV3APIError):
            self.client.put('/fake/url/', {})

    @patch('requests.put')
    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def test_put_vault_agent(self, mock_get_svc_account_password, mock_requests_put):
        """Tests that when first reponse on a put is a 401, vault credentials are 
        re-retrieved and HTTP put request is made again
        """

        global request_count
        request_count = 0
        mock_get_svc_account_password.return_value = 'password'

        mock_requests_put.side_effect = mock_request_method_vault
        self.vault_agent_client.put('/fake/url/', {})
        assert mock_get_svc_account_password.call_count == 1

    @patch('requests.delete', return_value=MockResponse(200, 'OK'))
    def test_delete_ok(self, mock_requests_delete):
        """Tests that when delete doesn't raise any errors when a request is fine
        """

        self.client.delete('/fake/url/')

    @patch('requests.delete', return_value=MockResponse(400, 'OK'))
    def test_delete_fail(self, mock_requests_delete):
        """Tests that when delete raises PulpV3APIError when failure HTTP code is returned
        """

        with pytest.raises(PulpV3APIError):
            self.client.delete('/fake/url/')

    @patch('requests.delete')
    @patch('pulp3.client.HashiVaultClient.get_svc_account_password')
    def test_delete_vault_agent(self, mock_get_svc_account_password, mock_requests_delete):
        """Tests that when first reponse on a delete is a 401, vault credentials are 
        re-retrieved and HTTP delete request is made again
        """

        global request_count
        request_count = 0
        mock_get_svc_account_password.return_value = 'password'

        mock_requests_delete.side_effect = mock_request_method_vault
        self.vault_agent_client.delete('/fake/url/')
        assert mock_get_svc_account_password.call_count == 1


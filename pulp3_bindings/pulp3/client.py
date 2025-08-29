"""Client for making requests to pulp
"""

import json
import requests
from hashi_vault_client.hashi_vault_client.client import HashiVaultClient

from .exceptions import PulpV3APIError


class Pulp3Client():
    """Pulp3 Client
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, address, username, password=None, use_vault_agent=False,
            vault_svc_account_mount='service-accounts', vault_agent_addr='http://127.0.0.1:8200',
            verify_ssl=True, use_https=True):
        """Constructor for Pulp3 client
        :param address: fqdn for the pulp server
        :type address: str
        :param username: username to connect to pulp api with
        :type username: str
        :param password: password for the user to connect to the API with
        :type password: str
        :param use_vault_agent: specified is the vault agent should be used to retrieve
                                the password for connecting to pulp with. When this method
                                if used credentials are refreshed when a 401 is returned
                                from the Pulp API. If a 401 is returned 3 times in a row
                                then an excpetion is thrown
        :type use_vault_agent: bool
        :param vault_agent_addr: Address to use for communicating with the vault agent.
                                 Defaults to http://127.0.0.1:8200
        :type vault_agent_addr: str
        :param vault_svc_account_mount: path that service accounts are stored in vault.
                                        Only used when use_vault_agent is set to True.
                                        Defaults to service-accounts
        :verifiy_ssl: Specifies if the SSL certificate of the Pulp server should be checked
        :type verify_ssl: true
        :param use_https: Specifies if the client should use https or http
        :type use_https: bool
        """

        self._address = address
        self._base_url = "{protocol}://{address}/pulp/api/v3".format(
            protocol='https' if use_https else 'http', address=address)
        self._username = username
        self._password = password
        self._use_vault_agent = use_vault_agent
        self._vault_svc_account_mount = vault_svc_account_mount
        self._vault_agent_addr = vault_agent_addr
        self._use_https = use_https
        self._verify_ssl = verify_ssl and use_https

        # Number of times to retry an API call if 401 was returned
        # only retry when using vault agent
        self._generic_failure_max_retries = 3
        self._auth_failure_max_retries = 3 if use_vault_agent else 1

        self._auth = None
        self._set_auth_headers()
        self._headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _set_auth_headers(self):
        """Sets the _auth header tuple. Retrieves service account password from vault
        if use_vault_agent was set to true when constructing the client
        """

        if self._use_vault_agent:
            hashi_vault_client = HashiVaultClient(url=self._vault_agent_addr, vault_agent=True)
            self._password = hashi_vault_client.get_svc_account_password(
                self._username, self._vault_svc_account_mount
            )

        self._auth = (self._username, self._password)

    # pylint: disable=no-self-use
    def _format_href(self, href):
        """Formats the href so that it is in the correct format. Stripping /pulp/api/v3
        :param href: href to format
        :type href: str
        :return: str
        """

        if '/pulp/api/v3' in href:
            return href.replace('/pulp/api/v3', '')
        return href

    # pylint: disable=no-self-use
    def _request_error_handler(self, method, response, url):
        """Helper for checking if there were any errors in the response.
        If errors are found then environment exception is raised.
        Response is considered an error when the response code is not in 200, 201 or 204
        :param method: HTTP method being called
        :type method: str
        :param response: response that was returned from the API request
        :type response: requests.models.Response
        :param url: URL of API request
        :type url: str
        """

        if response.status_code not in [200, 201, 202, 204]:
            message = (
                "Problem calling {0} {1}. "
                "HTTP Status Code: {2}. "
                "HTTP response text: {3}"
            ).format(method, url, response.status_code, response.text)
            raise PulpV3APIError(message)

    def get(self, api_method, params=None):
        """Carries out a HTTP GET request
        :param api_method: API method to call, pulp/api/v3 needs to be omitted
        :type api_method: str
        :param params: dict of options to be appended to the get request
        :type params: dict
        :return: requests.models.Response
        """

        if params is None:
            params = {}

        # Build query string k1=v1&k2=v3...
        query_string = ""
        for key, value in params.items():
            if isinstance(value, list):
                for list_value in value:
                    query_string += f"&{key}={list_value}"
            else:
                query_string += f"&{key}={value}"

        href = self._format_href(api_method)
        url = '{0}{1}?{2}'.format(self._base_url, href, query_string)
        # If we have the address of pulp in the _get request that most likey means
        # we have been given a full path to a resource or URL
        if self._address in api_method:
            url = api_method
            # ensure not sending password unencrypted when use_https is set to true
            if url.startswith('http://') and self._use_https:
                url = url.replace('http://', 'https://')

        auth_fail_retry_count = 0
        generic_fail_retry_count = 0
        while (auth_fail_retry_count < self._auth_failure_max_retries and
                generic_fail_retry_count < self._generic_failure_max_retries):
            response = requests.get(
                url,
                auth=self._auth,
                headers=self._headers,
                verify=self._verify_ssl
            )
            if(response.status_code == 401 and
                    auth_fail_retry_count < self._auth_failure_max_retries):
                auth_fail_retry_count += 1
                self._set_auth_headers()
                continue
            if response.status_code != 200:
                generic_fail_retry_count += 1
                continue

            return response.json()
        self._request_error_handler('GET', response, url)
        return response.json()

    def get_page_results(self, api_method, params=None):
        """Carries out a HTTP GET and if the results contains a next page
        retrieves these until there are no more pages
        :param api_method: API method to call
        :type api_method: str
        :param params: dict of options to be appened to the get request
        :type params: dict
        :return: list
        """

        items = []
        response = self.get(api_method, params)

        if response is None:
            return []

        if response['next']:
            items = self.get_page_results(response['next']) + items
        items = response['results'] + items
        return items

    def post(self, api_method, body=None):
        """Carries out a HTTP POST request
        :param api_method: API method to call, pulp/api/v3 needs to be omitted
        :type api_method: str
        :param body: dict to send as json body
        :type body: dict
        :return: requests.models.Response
        """

        if body is None:
            body = {}

        api_method = self._format_href(api_method)
        url = ''.join([self._base_url, api_method])

        auth_fail_retry_count = 0
        while auth_fail_retry_count < self._auth_failure_max_retries:
            response = requests.post(
                url,
                auth=self._auth,
                headers=self._headers,
                verify=self._verify_ssl,
                data=json.dumps(body)
            )

            if(response.status_code == 401 and
                    auth_fail_retry_count < self._auth_failure_max_retries):
                auth_fail_retry_count += 1
                self._set_auth_headers()
                continue

            self._request_error_handler('POST', response, url)
            return response.json()

    def put(self, api_method, body):
        """Carries out a HTTP PUT request
        :param api_method: API method to call, pulp/api/v3 needs to be omitted
        :type api_method: str
        :param body: dict to send as json body
        :type body: dict
        :return: requests.models.Response
        """

        api_method = self._format_href(api_method)
        url = ''.join([self._base_url, api_method])

        auth_fail_retry_count = 0
        while auth_fail_retry_count < self._auth_failure_max_retries:
            response = requests.put(
                url,
                auth=self._auth,
                headers=self._headers,
                verify=self._verify_ssl,
                data=json.dumps(body)
            )

            if(response.status_code == 401 and
                    auth_fail_retry_count < self._auth_failure_max_retries):
                auth_fail_retry_count += 1
                self._set_auth_headers()
                continue

            self._request_error_handler('PUT', response, url)
            return response.json()

    def patch(self, api_method, body):
        """Carries out a HTTP PATCH request
        :param api_method: API method to call, pulp/api/v3 needs to be omitted
        :type api_method: str
        :param body: dict to send as json body
        :type body: dict
        :return: requests.models.Response
        """

        api_method = self._format_href(api_method)
        url = ''.join([self._base_url, api_method])

        auth_fail_retry_count = 0
        while auth_fail_retry_count < self._auth_failure_max_retries:
            response = requests.patch(
                url,
                auth=self._auth,
                headers=self._headers,
                verify=self._verify_ssl,
                data=json.dumps(body)
            )

            if(response.status_code == 401 and
                    auth_fail_retry_count < self._auth_failure_max_retries):
                auth_fail_retry_count += 1
                self._set_auth_headers()
                continue

            self._request_error_handler('PATCH', response, url)
            return response.json()

    def delete(self, api_method):
        """Carries out a HTTP DELETE request
        :param api_method: API method to call, pulp/api/v3 needs to be omitted
        :type api_method: str
        :return: requests.models.Response
        """

        api_method = self._format_href(api_method)
        url = ''.join([self._base_url, api_method])

        auth_fail_retry_count = 0
        while auth_fail_retry_count < self._auth_failure_max_retries:
            response = requests.delete(
                url,
                auth=self._auth,
                headers=self._headers,
                verify=self._verify_ssl
            )

            if(response.status_code == 401 and
                    auth_fail_retry_count < self._auth_failure_max_retries):
                auth_fail_retry_count += 1
                self._set_auth_headers()
                continue

            self._request_error_handler('DELETE', response, url)
            return response.json()

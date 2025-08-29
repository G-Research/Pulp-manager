import os
import pytest
from pytest_mock import mocker
from datetime import datetime, timedelta

from mock import patch

from sys import path
path.append('.')
from hashi_vault_client.hashi_vault_client import HashiVaultClient
from hashi_vault_client.hashi_vault_client import HashiVaultException


class TestHashiVaultClient:
    """Class of test for the hash client
    """

    def setup_method(self):
        """Setup common vars for all tests
        """

        self.client = HashiVaultClient('http://localhost:8200', vault_agent=True)
        self.client2 = HashiVaultClient('http://localhost:8200')

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.unwrap')
    @patch('hashi_vault_client.client.hvac.v1.Client.write')
    @patch('hashi_vault_client.client.hvac.api.auth_methods.approle.AppRole.login')
    def test_assume_approle_login(self, mock_approle_login, mock_write, mock_unwrap):
        """Tests the assume approle login process. This is A workflow
        """

        tokens = [
            {
                'auth': {'client_token': 'token2'}
            },
            {
                'auth': {'client_token': 'token1'}
            }
        ]

        def side_effect_approle_login(assume_role_id, assume_secret_id, role_name, role_id):
            """Fake function to provide tokens across multiple logins
            """

            return tokens.pop()

        mock_approle_login.side_effect = side_effect_approle_login
        mock_write.return_value = {
            'wrap_info': {'token': 'fake-token'}
        }
        mock_unwrap.return_value = {
            'data': {'secret_id': 'secret1'}
        }

        # Token on client should be token2 as a result of the double login
        self.client2.assume_approle_login('111', '2222', 'role', '333')
        assert self.client2._client.token == 'token2'

        # Test when logging in with a client configured to use vault agent login fails
        with pytest.raises(HashiVaultException):
            self.client.assume_approle_login('111', '2222', 'role', '333')

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_list_mounts(self, mock_list_mounts):
        """Tests mounts are list when called
        """
        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'cubbyhole/': {
                    'accessor': 'ns_cubbyhole_b0730720',
                    'config': {
                        'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': 'per-token private secret storage',
                    'external_entropy_access': False,
                    'local': True,
                    'options': None,
                    'seal_wrap': False,
                    'type': 'ns_cubbyhole',
                    'uuid': '8aa48c2b-2906-0a2f-075d-9eea8f044f9b'
                },
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '1'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        seen = self.client.list_mounts()
        assert seen == mock_response

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_1_1(self, mock_list_mounts):
        """Testing v1 kv detection when kv options data contains version 1 explicitly
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '1'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        expected = 1
        seen = self.client.get_kv_version()
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_1_2(self, mock_list_mounts):
        """Testing v1 kv detection when kv options data contains empty hash of options
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        expected = 1
        seen = self.client.get_kv_version()
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_2_1(self, mock_list_mounts):
        """Testing v2 kv detection when kv options is set to none
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': None,
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        expected = 2
        seen = self.client.get_kv_version()
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_2_2(self, mock_list_mounts):
        """Testing v2 kv detection when kv options is set to 2 explicitly
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '2'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        expected = 2
        seen = self.client.get_kv_version()
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_2_3(self, mock_list_mounts):
        """Testing v2 kv detection when kv options is set but doesn't explictly say version 2
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'meta': 'blah'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response
        expected = 2
        seen = self.client.get_kv_version()
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_get_kv_version_fail(self, mock_list_mounts):
        """Testing failure when there is an unexpected kv version
        """

        # Cutdown version of a real response from vault
        mock_response = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '3'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_mounts.return_value = mock_response

        with pytest.raises(HashiVaultException):
            self.client.get_kv_version()


    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.list_secrets')
    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_list_kv_secrets_v1(self, mock_list_mounts, mock_list_secrets):
        """Tests listing the secrets in a kv1 store
        """

        # Cutdown version of a real response from vault
        mock_list_mounts.return_value = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '1'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_secrets.return_value = {
            'request_id': '8ceae606-3e8f-3372-7d4e-f70498aa0926',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 0,
            'data': {'keys': ['jenkins/', 'something_useful']},
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected = ['jenkins/', 'something_useful']
        seen = self.client.list_kv_secrets()

        assert seen == expected

    # This first patch may looks a bit weird when looking at the call made to list
    # secrets in the client code. But it is because secrets.kv.list_secrets is a call
    # to hvac.api.secrets_engines.kv_v2.KvV2 and not hvac.api.secrets_engines.kv.Kv
    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.list_secrets')
    @patch('hashi_vault_client.client.hvac.api.system_backend.SystemBackend.list_mounted_secrets_engines')
    def test_list_kv_secrets_v2(self, mock_list_mounts, mock_list_secrets):
        """Tests listing the secrets in a kv1 store
        """

        # Cutdown version of a real response from vault
        mock_list_mounts.return_value = {
            'data': {
                'kv/': {
                    'accessor': 'kv_f67b47f9',
                    'config': {'default_lease_ttl': 0, 'force_no_cache': False, 'max_lease_ttl': 0
                    },
                    'description': '',
                    'external_entropy_access': False,
                    'local': False,
                    'options': {'version': '2'},
                    'seal_wrap': False,
                    'type': 'kv',
                    'uuid': '0a16206f-686f-9708-8e99-5f7deb491944'
                }
            }
        }

        mock_list_secrets.return_value = {
            'request_id': '8ceae606-3e8f-3372-7d4e-f70498aa0926',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 0,
            'data': {'keys': ['jenkins/', 'something_useful']},
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected = ['jenkins/', 'something_useful']
        seen = self.client.list_kv_secrets()

        assert seen == expected

    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.read_secret')
    def test_read_kv_secret_v1(self, mock_read_secret, mock_get_kv_version):
        """Test reading the secret for a kv1 datasotre
        """

        mock_get_kv_version.return_value = 1
        mock_read_secret.return_value = {
            'request_id': '6715904b-69a0-970e-f0a4-6a7f1d8d06b2',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 14400,
            'data': {'password': 'fake_password'},
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected = {'password': 'fake_password'}
        seen = self.client.read_kv_secret('/fake-path')

        assert seen == expected

    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.read_secret_version')
    def test_read_kv_secret_v2(self, mock_read_secret, mock_get_kv_version):
        """Test reading the secret for a kv1 datasotre
        """

        mock_get_kv_version.return_value = 2
        mock_read_secret.return_value = {
            'request_id': '5cdff907-d569-021e-e164-a7852bf22761',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 0,
            'data': {
                'data': {
                    'password': 'fake_password',
                },
                'metadata': {
                    'created_time': '2020-04-20T15:59:09.133894466Z',
                    'deletion_time': '',
                    'destroyed': False,
                    'version': 5
                }
            },
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected = {'password': 'fake_password'}
        seen = self.client.read_kv_secret('/fake-path')

        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.create_or_update_secret')
    def test_merge_kv_secrets_kv1(self, mock_create_or_update_secret):
        """Test when _merge_kv_secrets called for a kv1 datastore the correct are passed
        """

        name = 'kv'
        version = 1
        path = '/fake-path'
        secret = {
            'k1': 'f',
            'k3': 'z'
        }
        existing_secrets = {
            'k1': 'a',
            'k2': 'b'
        }

        self.client._merge_kv_secrets(name, version, path, secret, existing_secrets)

        called_args, called_kwargs = mock_create_or_update_secret.call_args

        # Secret takes precendence so we expect k1 to be f
        expected = {
            'path': path,
            'secret': {
                'k1': 'f',
                'k2': 'b',
                'k3': 'z'
            },
            'mount_point': 'kv'
        }

        assert called_kwargs == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.create_or_update_secret')
    def test_merge_kv_secrets_kv2(self, mock_create_or_update_secret):
        """Test when _merge_kv_secrets called for a kv2 datastore the correct are passed
        """

        name = 'kv'
        version = 2
        path = '/fake-path'
        secret = {
            'k1': 'f',
            'k3': 'z'
        }
        existing_secrets = {
            'k1': 'a',
            'k2': 'b'
        }

        self.client._merge_kv_secrets(name, version, path, secret, existing_secrets)

        called_args, called_kwargs = mock_create_or_update_secret.call_args

        # Secret takes precendence so we expect k1 to be f
        expected = {
            'path': path,
            'secret': {
                'k1': 'f',
                'k2': 'b',
                'k3': 'z'
            },
            'mount_point': 'kv'
        }

        assert called_kwargs == expected

    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.list_kv_secrets')
    @patch('hashi_vault_client.HashiVaultClient.read_kv_secret')
    def test_add_kv_secret_expected_fail(self, mock_read_kv_secret, mock_list_kv_secrets,
            mock_get_kv_version):
        """Test that adding secrets to a kv fails when a matching key alrady exists
        """

        mock_get_kv_version.return_value = 1
        mock_list_kv_secrets.return_value = ['secret1', 'secret2', 'mysecret']
        mock_read_kv_secret.return_value = {
            'key': 'value'
        }

        with pytest.raises(HashiVaultException):
            self.client.add_kv_secret('/mysecret', { 'key': 'new_value' }, 'kv')

    @patch('hashi_vault_client.HashiVaultClient._merge_kv_secrets')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.list_kv_secrets')
    @patch('hashi_vault_client.HashiVaultClient.read_kv_secret')
    def test_add_kv_secret_expected_merge(self, mock_read_kv_secret, mock_list_kv_secret,
            mock_get_kv_version, mock_merge_kv_secrets):
        """Tests that add a new key value to an existing secret succeds when there is no key clash
        """

        mock_list_kv_secret.return_value = ['secret1', 'secret2', 'mysecret']
        mock_read_kv_secret.return_value = {
            'key': 'value'
        }
        mock_get_kv_version.return_value = 1

        # Nothing to assert of check we just expect no errors
        self.client.add_kv_secret('/mysecret', {'key2': 'value2'})

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.list_kv_secrets')
    def test_add_kv_secret_kv1(self, mock_list_kv_secrets, mock_get_kv_version,
        mock_create_or_update_secret):
        """Tests add a secret to a kv1 datastore succeds when the secret path doesn't exist
        """

        mock_list_kv_secrets.return_value = []
        mock_get_kv_version.return_value = 1

        self.client.add_kv_secret('/mysecret', {'key', 'value'})

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.list_kv_secrets')
    def test_add_kv_secret_kv2(self, mock_list_kv_secrets, mock_get_kv_version,
        mock_create_or_update_secret):
        """Tests add a secret to a kv2 datastore succeds when the secret path doesn't exist
        """

        mock_list_kv_secrets.return_value = []
        mock_get_kv_version.return_value = 2

        self.client.add_kv_secret('/mysecret', {'key', 'value'})

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    def test_update_kv_secret_no_merge_kv1(self, mock_get_kv_version, mock_create_or_update_secret):
        """Tests that calling update_kv_secret without merge causes create_or_update_secret to be called for kv1
        """

        mock_get_kv_version.return_value = 1
        self.client.update_kv_secret('/mysecret', {'key': 'value'}, merge=False)

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    def test_update_kv_secret_no_merge_kv2(self, mock_get_kv_version, mock_create_or_update_secret):
        """Tests that calling update_kv_secret without merge causes create_or_update_secret to be called for kv2
        """

        mock_get_kv_version.return_value = 2
        self.client.update_kv_secret('/mysecret', {'key': 'value'}, merge=False)

    @patch('hashi_vault_client.HashiVaultClient._merge_kv_secrets')
    @patch('hashi_vault_client.HashiVaultClient.read_kv_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    def test_update_kv_secret_with_merge(self, mock_get_kv_version, mock_read_kv_secret,
            mock_merge_kv_secrets):
        """Tests that when update kv secret called with merge there are no errors
        """

        mock_get_kv_version.return_value = 1
        mock_read_kv_secret.return_value = {'password1': 'pass'}
        self.client.update_kv_secret('/mysecret', {'key': 'value'})


    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.delete_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    def test_delete_kv_secret_v1(self, mock_get_kv_version, mock_delete_secret):
        """Tests delete secret for kv1 does not error
        """

        mock_get_kv_version.return_value = 1
        self.client.delete_kv_secret('/mysecret')

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.delete_metadata_and_all_versions')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    def test_delete_kv_secret_v2(self, mock_get_kv_version, mock_delete_metadata_and_all_versions):
        """Tests delete secret for kv2 does not error
        """

        mock_get_kv_version.return_value = 2
        self.client.delete_kv_secret('/mysecret')

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.read_kv_secret')
    def test_delete_kv_secret_keys_v1(self, mock_kv_read_secret, mock_get_kv_version,
            mock_create_or_update_secret):
        """Tests that deleting keys from a kv1 secret makes the correct method call, and passes the correct arguments
        for what should be overwritten
        """

        mock_kv_read_secret.return_value = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 'value4'
        }

        mock_get_kv_version.return_value = 1

        self.client.delete_kv_secret_keys(
            '/mysecret', ['key1', 'key3']
        )

        called_args, called_kwargs = mock_create_or_update_secret.call_args

        expected = {
            'key2': 'value2',
            'key4': 'value4'
        }

        assert called_kwargs['secret'] == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v2.KvV2.create_or_update_secret')
    @patch('hashi_vault_client.HashiVaultClient.get_kv_version')
    @patch('hashi_vault_client.HashiVaultClient.read_kv_secret')
    def test_delete_kv_secret_keys_v2(self, mock_kv_read_secret, mock_get_kv_version,
            mock_create_or_update_secret):
        """Tests that deleting keys from a kv2 secret makes the correct method call, and passes the correct arguments
        for what should be overwritten
        """

        mock_kv_read_secret.return_value = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
            'key4': 'value4'
        }

        mock_get_kv_version.return_value = 2

        self.client.delete_kv_secret_keys(
            '/mysecret', ['key1', 'key3']
        )

        called_args, called_kwargs = mock_create_or_update_secret.call_args

        expected = {
            'key2': 'value2',
            'key4': 'value4'
        }

        assert called_kwargs['secret'] == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.read_secret')
    def test_get_svc_account_password(self, mock_read_secret):
        """Tests the password is returned for a service account
        """

        mock_read_secret.return_value = {
            'request_id': '1d8388c0-8aba-a127-f02e-598c647ca609',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 0,
            'data': {
                'current_password': 'password',
                'username': 'svc-fake-account'
            },
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected = 'password'
        seen = self.client.get_svc_account_password('svc-fake-account')

        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.list_secrets')
    def test_list_local_admin_password_accounts(self, mock_list_secrets):
        """Tests that the call to list_local_password_accounts returns a list of paths
        """

        response = ['linux/team/fqdn.example.com', 'delegate/linux/team/fqdn.example.com']
        mock_list_secrets.return_value = response
        expected = response
        seen = self.client.list_local_password_accounts()

        assert seen == expected

    def test_get_linux_password_path_delegate(self):
        """Tests the correct password path is returned when requesting the delegate account
        """

        expected = 'delegate/linux/team/fqdn.example.com'
        seen = self.client._get_linux_password_path('fqdn.example.com', 'team', True)
        assert seen == expected

    def test_get_linux_password_path(self):
        """Tests the correct password path is returned for none delegate account
        """

        expected = 'linux/team/fqdn.example.com'
        seen = self.client._get_linux_password_path('fqdn.example.com', 'team', False)
        assert seen == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.read_secret')
    def test_get_linux_password(self, mock_read_secret):
        """Tests that the dict for an account is returned correctly
        """

        mock_read_secret.return_value = {
            'request_id': '8ac1a00b-a517-ee03-967c-89c5a086d9d4',
            'lease_id': '',
            'renewable': False,
            'lease_duration': 0,
            'data': {
                'cmd': 'sudo passwd {{ username }}',
                'delegate': True,
                'password': 'password',
                'port': 22,
                'tainted': True,
                'username': 'root',
                'winrm': False
            },
            'wrap_info': None,
            'warnings': None,
            'auth': None
        }

        expected =  {
            'cmd': 'sudo passwd {{ username }}',
            'delegate': True,
            'password': 'password',
            'port': 22,
            'tainted': True,
            'username': 'root',
            'winrm': False
        }

        seen = self.client.get_linux_password('fqdn.example.com', 'team', False)

        assert seen == expected

    @patch('hashi_vault_client.client.hvac.v1.Client.write')
    def test_add_or_update_linux_password(self, mock_write):
        """Tests that when a linux password is added/update the correct arguments are passed
        """

        expected = {
            'username': 'root',
            'password': 'password',
            'port': 22,
            'delegate': True,
            'method': 'POST'
        }

        self.client.add_or_update_linux_password(
            'fqdn.example.com', 'team', 'root', 'password', False)

        
        called_args, called_kwargs = mock_write.call_args

        assert called_kwargs == expected

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.delete_secret')
    def test_delete_secret(self, mock_delete_secret):
        """Tests that the call to delete password doesn't error
        """

        self.client.delete_linux_password('fqdn.example.com', 'team', False)

    @patch('hashi_vault_client.client.hvac.api.secrets_engines.kv_v1.KvV1.create_or_update_secret')
    def test_rotate_linux_password(self, mock_create_or_update_secret):
        """Tests calling rotate doesn't error out
        """

        self.client.rotate_linux_password('fqdn.example.com', 'team', False)

    @patch('hashi_vault_client.client.hvac.v1.Client.read')
    def test_get_github_token(self, mock_read):
        """Tests that the github token is successfully returned
        """

        mock_read.return_value = {"data": {"test-user": "token"}}
        result = self.client.get_github_token("test-user")
        assert result == "token"

    def test_get_cert_expiry_date(self):
        """Tests that the expiry date from an x509 pem is successfull returned
        Makes use of test cert test-cert.pem, which was generated with openssl for
        validating the date 
        """

        cert_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test-cert.pem')
        with open(cert_path, 'r') as cert_stream:
            expected = datetime(2023, 7, 14, 14, 0, 55)
            seen = self.client.get_cert_expiry_date(cert_stream.read())
            assert seen == expected

    @patch('hashi_vault_client.HashiVaultClient.get_cert_expiry_date')
    @patch('hashi_vault_client.client.hvac.api.secrets_engines.pki.Pki.read_ca_certificate')
    @patch('hashi_vault_client.client.hvac.api.secrets_engines.pki.Pki.generate_certificate')
    def test_request_ssl_cert(self, mock_generate_certificate, mock_read_ca_certificate,
            mock_get_cert_expiry_date):
        """Tests calls to request ssl cert results in the expected arguments being
        passed to the vult command
        """

        utc_now = datetime.utcnow()
        mock_get_cert_expiry_date.return_value = utc_now + timedelta(days=900)
        mock_read_ca_certificate.return_value = '--BEGIN CERT--fake stuff--END CERT--'

        expected = {
            'name': 'star-ccc-local',
            'common_name': 'host.domain.local',
            'extra_params': {'ttl': '365d'}
        }

        self.client.request_ssl_cert('star-ccc-local', 'host.domain.local')
        called_args, called_kwargs = mock_generate_certificate.call_args
        assert called_kwargs == expected

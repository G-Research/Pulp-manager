"""Definitionas for HashiVaultClient
"""
# pylint:disable=import-error
import hvac
from datetime import datetime, timedelta
from cryptography import x509


class HashiVaultException(Exception):
    """Custom exception type for HashiVaultClient
    """
    pass


class HashiVaultClient:
    """Wrapper around hvac for carrying out vault operations
    Not designed to carry out all the features vault has, for that
    best to stick to native hvac
    """

    # pylint:disable=too-many-arguments
    def __init__(self, url=None, token=None, cert=None, verify=True, timeout=30, proxies=None,
                 allow_redirects=True, session=None, adapter=hvac.adapters.JSONAdapter,
                 namespace=None, vault_agent=False, **kwargs):
        """Initialises the HashiVaultClient. Unless vault agent has been set, a login method
        needs to be called after initialisation

        :param url: Base URL for the Vault instance being addressed.
        :type url: str
        :param token: Authentication token to include in requests sent to Vault.
        :type token: str
        :param cert: Certificates for use in requests sent to the Vault instance. This should
            be a tuple with the certificate and then key.
        :type cert: tuple
        :param verify: Either a boolean to indicate whether TLS verification should be performed
            when sending requests to Vault, or a string pointing at the CA bundle to use for
            verification.
            See http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification.
        :type verify: Union[bool,str]
        :param timeout: The timeout value for requests sent to Vault.
        :type timeout: int
        :param proxies: Proxies to use when performing requests.
            See: http://docs.python-requests.org/en/master/user/advanced/#proxies
        :type proxies: dict
        :param allow_redirects: Whether to follow redirects when sending requests to Vault.
        :type allow_redirects: bool
        :param session: Optional session object to use when performing request.
        :type session: request.Session
        :param adapter: Optional class to be used for performing requests. If none is provided,
            defaults to hvac.adapters.JSONRequest
        :type adapter: hvac.adapters.Adapter
        :param kwargs: Additional parameters to pass to the adapter constructor.
        :type kwargs: dict
        :param namespace: Optional Vault Namespace.
        :type namespace: str
        :param vault_agent: Specifies if communication is taking splace via the vault agent
        :type vault_agent: bool
        """

        self._vault_agent = vault_agent
        self._verify = verify
        if vault_agent and url is None:
            url = 'http://localhost:8200'
        self._client = hvac.Client(url=url, token=token, cert=cert, verify=verify, timeout=timeout,
                                   proxies=proxies, allow_redirects=allow_redirects,
                                   session=session, adapter=adapter, namespace=namespace, **kwargs)

        # When hvac is setup it has a method called is_authenticated() and this will be set
        # to false as it expects to need to authenticate against vault. However you can set
        # the client token to be empty, and if you do that is_authenticated() returns true
        # and the hvac client can then interact with the vault agent
        if vault_agent:
            self._client.token = ''

    # pylint:disable=too-many-arguments
    def ldap_login(self, username, password, use_token=True, mount_point='ldap'):
        """Log in with LDAP credentials.

        Supported methods:
            POST: /auth/{mount_point}/login/{username}. Produces: 200 application/json

        :param username: The username of the LDAP user
        :type username: str | unicode
        :param password: The password for the LDAP user
        :type password: str | unicode
        :param use_token: if True, uses the token in the response received from the auth request
            to set the "token" attribute on the the :py:meth:`hvac.adapters.Adapter`
            instance under the _adapater Client attribute.
        :type use_token: bool
        :param mount_point: The "path" the method/backend was mounted on.
        :type mount_point: str | unicode
        :return: The response of the login_with_user request.
        :rtype: requests.Response
        """

        if self._vault_agent:
            raise HashiVaultException(
                'ldap_login not supported when client communiucation with vault agent')

        return self._client.auth.ldap.login(
            username=username, password=password, use_token=use_token, mount_point=mount_point)

    def approle_login(self, role_id, secret_id=None, use_token=True, mount_point='approle'):
        """
        Login with APPROLE credentials.
        Supported methods:
            POST: /auth/{mount_point}/login. Produces: 200 application/json
        :param role_id: Role ID of the role.
        :type role_id: str | unicode
        :param secret_id: Secret ID of the role.
        :type secret_id: str | unicode
        :param use_token: if True, uses the token in the response received from the auth request to
            set the "token" attribute on the the :py:meth:`hvac.adapters.Adapter` instance under the
            _adapater Client attribute.
        :type use_token: bool
        :param mount_point: The "path" the method/backend was mounted on.
        :type mount_point: str | unicode
        :return: The JSON response of the read_role_id request.
        :rtype: dict
        """

        if self._vault_agent:
            raise HashiVaultException(
                'approle_login not supported when client communiucation with vault agent')

        return self._client.auth.approle.login(
            role_id, secret_id, use_token, mount_point)

    # pylint:disable=too-many-arguments
    def assume_approle_login(self, assume_role_id, assume_secret_id, role_name,
                             role_id, root_namespace_login=True):
        """This is a login method where an aprole and secret id are used
        to generate a secret id for a role with a higher set of perms to access
        secrets from vault

        :param assume_role_id: role id to use to login to vault generate secret from the role_id
        :type assume_role_id: str
        :param assume_secret_id: secret id that belongs to the assume_role_id to do the first login
        :type assume_secret_id: str
        :param role_name: name of the role to generate secret id for. Required as secret-id
                          cannot be generated from a role id. But a role id is required for login
                          as it cannot be done by name
        :type role_name: str
        :param role_id: role id to generate secret for and login to vault with
        :type role_id: str
        :param root_namespace_login: specifies the login needs to be done via the root namespace
        :type root_namespace_login: bool
        :return: The JSON response of the read_role_id request.
        :rtype: dict
        """

        if self._vault_agent:
            raise HashiVaultException(
                'assume_approle_login not supported when client communiucation with vault agent')

        # In not all account/account types can login via vault namespace. So if
        # root_namespace_login was set to true, and a namespace was specified in
        # __init__, then we need to create a temporary client to get a token
        # which we can then set on self._client

        temp_client = self._client
        if root_namespace_login and self._client.adapter.namespace is not None:
            temp_client = hvac.Client(url=self._client.adapter.base_uri, verify=self._verify)

        # In some instances token on the client is automatically updates
        # does not seem to be the case with approle login, so store and set
        login_result = temp_client.auth.approle.login(
            assume_role_id, assume_secret_id, False, 'approle')
        temp_client.token = login_result['auth']['client_token']
        # At when secret ids are generated, they are returned as a wrapped secret
        # this means that the generate_secret_id method, for an approle can't be used.
        # So instead we have to do direct vault write and unwrap commands to get
        # the secret id
        result = temp_client.write(
            path='auth/approle/role/{0}/secret-id'.format(role_name),
            wrap_ttl='30s'
        )

        unwraped_response = temp_client.sys.unwrap(
            token=result['wrap_info']['token']
        )

        secret_id = unwraped_response['data']['secret_id']
        login2_result = temp_client.auth.approle.login(role_id, secret_id, False, 'approle')
        temp_client.token = login2_result['auth']['client_token']

        if root_namespace_login and self._client.adapter.namespace is not None:
            self._client.token = login2_result['auth']['client_token']

        return login2_result

    def list_mounts(self):
        """Returns a dictionary of mounts in namespace the client is in
        :return: JSON response of listing the mounts in the namespace
        :rtype: dict
        """

        return self._client.sys.list_mounted_secrets_engines()

    def get_kv_version(self, name='kv'):
        """Returns the version of the specified kv

        :param name: Name of the kv to list secrets for
        :type name: str
        :return: kv version number
        :rtype: int
        """

        mounts = self.list_mounts()
        # When mounts are returned from vault a / is added to the kv name, so need
        # to add when confirm the xistance of the requeted kv
        if name[-1] != '/':
            name = "{0}/".format(name)
        if name not in mounts['data'].keys():
            raise HashiVaultException(
                "kv with name '{0}' not found in list of mounts".format(name))

        if (mounts['data'][name]['options'] is not None and
                (len(mounts['data'][name]['options']) == 0 or
                 'version' in mounts['data'][name]['options'] and
                 mounts['data'][name]['options']['version'] == '1')):
            return 1
        elif (mounts['data'][name]['options'] is None or
              (len(mounts['data'][name]['options']) > 0 and
               'version' not in mounts['data'][name]['options'] or
               'version' in mounts['data'][name]['options'] and
               mounts['data'][name]['options']['version'] == '2')):
            return 2
        raise HashiVaultException(
            "kv version for '{0}' could not be determined".format(name[0:len(name) - 1]))

    def list_kv_secrets(self, name='kv', path='/'):
        """List the secrets for the given kv at the requested location

        :param name: Name of the kv to list secrets for
        :type name: str
        :param path: Path to read secrets from. Defaults to /
        :type path: str
        """

        version = self.get_kv_version(name)
        secrets = None
        if version == 1:
            secrets = self._client.secrets.kv.v1.list_secrets(path=path, mount_point=name)
        else:
            secrets = self._client.secrets.kv.list_secrets(path=path, mount_point=name)
        return secrets['data']['keys']

    def read_kv_secret(self, path, name='kv'):
        """Returns a dict of the secrets at the specified kv path.
        This method only return the key value pairs for a secret.
        If the kv is version 2, the metadata is not returned

        :param path: Path to read secret from within the kv
        :type str:
        :param name: Name of the kv to read the secrets from
        :type name: str
        :return: key value pairs that make up the secret
        :rtype: dict
        """

        version = self.get_kv_version(name)
        if version == 1:
            return self._client.secrets.kv.v1.read_secret(path=path, mount_point=name)['data']
        else:
            return self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=name)['data']['data']

    # pylint:disable=too-many-arguments
    def _merge_kv_secrets(self, name, version, path, secret, existing_secrets):
        """Takes the exsiting secrets and new secrets to be added to a kv
        merges the two dicts and then updates vault at the specified path.
        If being called to merge dictionaries where there are keys that exist
        in both secret and existing_secrets, then the value for the key in secret
        takes precendence

        :param name: name of the kv to merge secrets in
        :type name: str
        :param version: version that the kv is
        :type version: int
        :param path: path in the kv to update the secrets of
        :type path: str
        :param secret: secrets to merge into kv
        :type secret: dict
        :param existing_secrets: existing secrets in the kv
        :type existing_secrets: dict
        """

        # Copy exist_secrets dict and then update
        # with the value from secret, to ensure the
        # new secrets take precedence when matching keys exist
        merged_secrets = existing_secrets.copy()
        merged_secrets.update(secret)

        if version == 1:
            self._client.secrets.kv.v1.create_or_update_secret(
                path=path, secret=merged_secrets, mount_point=name)
        else:
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path, secret=merged_secrets, mount_point=name)

    def add_kv_secret(self, path, secret, name='kv'):
        """Adds the dict of secrets to the specified kv path.
        If the kv being added to already has a secret with
        one the keys matching what is requesting to be added then
        an exception is thrown, otherwise requested secret to add is merged
        with existing secrets

        :param path: path to store the secrets at
        :type path: str
        :param secret: dict of secrets to store at the path
        :type secret: dict
        :param name: name of the kv to be storing the secrets at
        :type name: str
        """

        # First list the secrets at the kv path to see if they exist.
        # assume the following two paths:
        # 1. /mysecret
        # 2. /some/very/long/path/mysecret
        # In both cases my secret is the leaf which contains the key value
        # pairs that makeup the secret
        # Therefore we want to check for the presence of mysecret. If it does
        # not exist we can safely create a new secret. If mysecret was to exist
        # then we check the existing key value pairs and if no keys clash
        # we just merge the contents, otherwise we throw and error. Which
        # would force user to then call update_kv_secret method

        # paths can be given in two formats. / if not at start of path so logic works
        if path[0:1] != '/':
            path = '/{0}'.format(path)
        path_split = path.split('/')
        leaf = path_split[len(path_split) - 1]
        parent = path[0:path.rfind('{0}'.format(leaf))]
        existing_secrets = self.list_kv_secrets(name, parent)
        version = self.get_kv_version(name)

        if leaf in existing_secrets:
            # Get the values for the secrets at the requested path
            # This returns a dict, compare the keys here
            # with those requested in the new secret
            existing_secret_values = self.read_kv_secret(path, name)
            existing_secret_keys = existing_secret_values.keys()
            new_secret_keys = list(secret.keys())
            common_keys = list(set(existing_secret_keys).intersection(new_secret_keys))
            if len(common_keys) != 0:
                raise HashiVaultException(
                    "The following keys '{0}' already exist at '{1}' for kv '{2}'".format(
                        ', '.join(common_keys), path, name)
                )
            else:
                self._merge_kv_secrets(name, version, path, secret, existing_secret_values)
        else:
            if version == 1:
                self._client.secrets.kv.v1.create_or_update_secret(
                    path=path, secret=secret, mount_point=name)
            else:
                self._client.secrets.kv.v2.create_or_update_secret(
                    path=path, secret=secret, mount_point=name)

    def update_kv_secret(self, path, secret, name='kv', merge=True):
        """Updates the kv with specified secret dict.

        :param path: path to update the secrets at
        :type path: str
        :param secret: dict of secrets to update at specified path
        :type secret: dict
        :param name: name of kv to update secrets of
        :type name: str
        :param merge: when set to true, the values of secret are merged with existing
                      secrets in the kv. If they are keys in secret which already exist
                      in the patch specified then the value of the key in secret takes
                      precedence. When set to false, the values in the kv are overwritten
        :type param: str
        """

        version = self.get_kv_version(name)
        if not merge:
            if version == 1:
                self._client.secrets.kv.v1.create_or_update_secret(
                    path=path, secret=secret, mount_point=name)
            else:
                self._client.secrets.kv.v2.create_or_update_secret(
                    path=path, secret=secret, mount_point=name)
        else:
            existing_secrets = self.read_kv_secret(path, name)
            self._merge_kv_secrets(name, version, path, secret, existing_secrets)

    def delete_kv_secret(self, path, name='kv'):
        """Deletes all the secrets at the given path. This method doesn't support any
        of the special kv 2 delete API calls for preserving some meta data/secret
        versions, it is a destructive delete

        :param path: path to kv secret to delete
        :type path: str
        :param name: name of kv to remove the secret from
        :type name: str
        """

        version = self.get_kv_version(name)
        if version == 1:
            self._client.secrets.kv.v1.delete_secret(path=path, mount_point=name)
        else:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path, mount_point=name)

    def delete_kv_secret_keys(self, path, keys, name='kv'):
        """Deletes the requested keys from the specified secret path

        :param path: path to kv secret to remove keys from
        :type path: str
        :param keys: keys to remove from existing secret
        :type keys: list
        :param name: name of the kv to remove keys from
        :type name: str
        """

        kv_secrets = self.read_kv_secret(path, name)
        for key in keys:
            del kv_secrets[key]

        version = self.get_kv_version(name)
        if version == 1:
            self._client.secrets.kv.v1.create_or_update_secret(
                path=path, secret=kv_secrets, mount_point=name)
        else:
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path, secret=kv_secrets, mount_point=name)

    def get_svc_account_password(self, svc_account, svc_account_mount='service-accounts'):
        """Retrieves the specified service account password from vault

        :param svc_account: name of service account tyo get password of
        :type svc_account: str
        :param svc_account_mount: mount point of service account creds. Defaults to
                                  service-acocunts.
        :type svc_account_mount: str
        :return: data of the kv containg service account password
        :rtype: dict
        """

        # Currently service accounts are stored in kv 1 in root namespace
        # kv called service-accounts
        # path to password is /creds/server-account-name
        return self._client.secrets.kv.v1.read_secret(
            mount_point=svc_account_mount,
            path='/creds/{0}'.format(svc_account)
        )['data']['current_password']

    def list_local_password_accounts(self):
        """Returns list of accounts stored in the password mount

        :return: list of passwords stored in the password mount
        :rtype: list
        """

        # passwords are stored in a kv1 namespace called password.
        # /status is a bith which contains the list of accounts that
        # are set. Where an account is in the format:
        # delegate/linux/CoreLinuxEngineering/cezcledummy4.example.com

        return self._client.secrets.kv.v1.list_secrets(path='/status', mount_point='password')

    # pylint:disable=no-self-use
    def _get_linux_password_path(self, name, owner, delegate):
        """Return the path the computer account password should be
        located at in vault

        :param name: name of the computer account to be stored in vault
        :type name: str
        :param owner: owner of the computer account
        :type owner: str
        :param delegate: specifies if delegate account is being added
        :type delegate: bool
        :return: path to where computer account password stored in vault
        :rtype: str
        """

        if delegate:
            return 'delegate/linux/{0}/{1}'.format(owner, name)
        return 'linux/{0}/{1}'.format(owner, name)

    def get_linux_password(self, name, owner, delegate):
        """Retrieves secres associated with an account
        {
            'cmd': 'sudo passwd {{ username }}',
            'delegate': False, 'password': 'xxxx',
            'port': 22,
            'tainted': True,
            'username': 'reconcile',
            'winrm': False
        }

        :param name: name of the computer account to get password of
        :type name: str
        :param owner: owner of the computer account
        :type owner: str
        :param delegate: specifies if delegate account should be retrieved
        :type delegate: bool
        :return: data about the account
        :rtype: dict
        """

        path = '/{0}'.format(self._get_linux_password_path(name, owner, delegate))
        return self._client.secrets.kv.v1.read_secret(path, mount_point='password')['data']

    # pylint:disable=too-many-arguments
    def add_or_update_linux_password(self, name, owner, username, password, delegate):
        """Adds or updates a password in vault for a linux comptuer account
        Used for supporting the root password rotation feature

        :param name: name of computer account to add
        :param owner: owner of the computer, used for team section for where to place in vault
        :param username: username to be associated with the path being placed at.
                         Usually root or reconcile
        :param password: password to associate with account
        :param delegate: specifies the delegate account is being added. This changes the
                         path where the account is stored in vault. The delegate account
                         is used to rotate the root password
        """

        path = '/password/register/{0}'.format(self._get_linux_password_path(name, owner, delegate))
        account_delegated = False

        # A bit of a weird way in how the module was written. The root password
        # which is rotated by delegate needs to have delegate set to true in its
        # body. This this is to show the account is tied to a delegate account
        if not delegate:
            account_delegated = True

        # Need to call vault write, if you try and call add_or_update operation
        # an unsupported operation will be thrown. Additionally can't use the value
        # secret, need to give each of the paramters that we want to store
        self._client.write(
            path, username=username, password=password, port=22,
            delegate=account_delegated, method='POST'
        )

    def delete_linux_password(self, name, owner, delegate):
        """Deletes the linux password from vault

        :param name: name of computer account password to remove
        :param owner: owner of computer
        :param deleage: when sets to true remove delegate account. False removes root
        """

        path = '/{0}'.format(self._get_linux_password_path(name, owner, delegate))
        self._client.secrets.kv.v1.delete_secret(path=path, mount_point='password')

    def rotate_linux_password(self, name, owner, delegate):
        """Rotates the specified account password in vault

        :param name: name of computer account password to rotate password for
        :param owner: owner of computer
        :param deleage: when sets to true rotates delegate account. False rotates root
        """

        # The rotate works by forcefully writing to a rotate endpoint
        # so we call rotate with an empty secret so the vault command
        # does not error
        path = '/rotate/{0}'.format(self._get_linux_password_path(name, owner, delegate))
        self._client.secrets.kv.v1.create_or_update_secret(
            path=path, mount_point='password', secret={}, method='POST')

    def get_github_token(self, username):
        """Gets the requested github token
        """

        return self._client.read("githubtokens/token/{0}".format(username))["data"][username]

    def get_cert_expiry_date(self, cert):
        """Returns the date when a x509 cert will expire. The Cert is expected
        to be in a pem format which is was is returned from hvacs
        hvac.api.secrets_engines.pki.read_ca_certificate()

        :param ca_cert: PEM cert to get expiry date from as string
        :return: DateTime
        """

        return x509.load_pem_x509_certificate(cert.encode()).not_valid_after


    def request_ssl_cert(self, role_name, common_name, alt_names = None):
        """Requests an SSL cert from vault. Attempts to request a cert that lasts a year
        however if the vault CA cert is due to expire in that time, it will request a cert
        with a shortter lifetime so that vault doesn't error about the cert requested
        being beyond the CA's expiry date

        :param role_name: Name of the PKI role to request from e.g. star-ccc-local
        :param common_name: Common name for the cert
        :param alt_names: Specifies requested Subject Alternative Names, in a comma-delimited list.
                          These can be host names or email addresses; they will be parsed into their
                          respective fields. If any requested names do not match role policy, the
                          entire request will be denied.
        :return: Dict signed cert data. Important keys: ca_chain, certificate,
                 issuing_ca, private_key
        """

        # First get the vault CA public key to get when the cert will expire. This returns a pem
        vault_ca_cert = self._client.secrets.pki.read_ca_certificate()
        vault_ca_cert_expiry = self.get_cert_expiry_date(vault_ca_cert)
        date_1_year_in_future = datetime.utcnow() + timedelta(days=365)
        cert_ttl_days = 365

        if vault_ca_cert_expiry < date_1_year_in_future:
            cert_ttl_days = (vault_ca_cert_expiry - datetime.utcnow()).days

        # List of options can be found at: https://www.vaultproject.io/api-docs/secret/pki
        extra_params = {'ttl': '{0}d'.format(cert_ttl_days)}
        if alt_names:
            extra_params['alt_names'] = alt_names

        # https://hvac.readthedocs.io/en/stable/source/hvac_api_secrets_engines.html
        # search for generate_certificate
        return self._client.secrets.pki.generate_certificate(
            name=role_name, common_name=common_name, extra_params=extra_params) 

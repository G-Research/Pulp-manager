"""Tests the service that carries out the registering of repos
"""

import json
import os
import shutil

import pytest
from mock import mock_open, patch

from pulp_manager.app.database import engine, session
from pulp_manager.app.services.repo_config_register import RepoConfigRegister


class TestRepoConfigRegister:
    """Carries out tests of registering repos in pulp from config files that are held in git
    """

    @patch("pulp_manager.app.services.repo_config_register.PulpManager", autospec=True)
    def setup_method(self, method, mock_pulp_manager):
        """Setup mocks
        """

        # Use a pulp server from the sample data insert
        self.db = session()
        self.repo_config_register = RepoConfigRegister(self.db, "pulpserver1.domain.local")

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()
        engine.dispose()

    @patch("pulp_manager.app.services.repo_config_register.Repo.clone_from")
    def test_clone_pulp_repo_config(self, mock_clone_from):
        """Tests that a directory gets created which would contain checked out code from git
        """

        def clone_from(url, to_path):
            """Creates the repo_config directory in the to_path, as this would exist
            once the repo has been checked out
            """

            repo_config_path = os.path.join(to_path, "repo_config")
            os.mkdir(repo_config_path)

        mock_clone_from.side_effect = clone_from

        git_clone_dir = self.repo_config_register._clone_pulp_repo_config()
        assert os.path.isdir(git_clone_dir)
        shutil.rmtree(git_clone_dir)

    @patch("pulp_manager.app.services.repo_config_register.os.path.isfile")
    @patch("pulp_manager.app.services.repo_config_register.HashiVaultClient.read_kv_secret")
    def test_generate_repo_config_from_file_external_rpm(self, mock_read_kv_secret, mock_isfile):
        """Tests that the correct repo config is generated for a remote repo
        """

        mock_isfile.return_value = True

        fake_file_path = "/home/user/git/pulp_repo/remote/el7/repo.json"
        # Code assume there will be a global file after first instance of remote
        fake_global_path = "/home/user/git/pulp_repo/remote/global.json"
        mock_read_kv_secret.return_value = {
            "ca_cert": "CA_CERT",
            "client_cert_key": "CLIENT_CERT_KEY"
        }

        mock_open_data = {
            fake_file_path: json.dumps({
                "name": "rhel8s-baseos",
                "url": "https://cdn.redhat.com/content/dist/rhel8/8/x86_64/baseos/os",
                "owner": "Core Linux Engineering",
                "description": "RHEL 8 Base OS repo",
                "repo_type": "external",
                "content_repo_type": "rpm",
                "publish_latest": True,
                "base_url": "rhel8s-x86_64",
                "ca_cert": "redhat-uep.pem",
                "client_cert": "redhat_client.pem",
                "client_key": "redhat_client.pem",
                "tls_validation": True,
                "vault_load_secrets": [
                    {
                        "kv": "kv",
                        "path": "/redhat-license-certs",
                        "secret_name": "ca_cert",
                        "remote_property": "ca_cert"
                    },
                    {
                        "kv": "kv",
                        "path": "/redhat-license-certs",
                        "secret_name": "client_cert_key",
                        "remote_property": "client_cert"
                    },
                    {
                        "kv": "kv",
                        "path": "/redhat-license-certs",
                        "secret_name": "client_cert_key",
                        "remote_property": "client_key"
                    }
                ]
            }),
            fake_global_path: json.dumps({
                "proxy": "http://proxy.example.com:8080"
            })
        }

        def open_side_effect(name, mode=None):
            return mock_open(read_data=mock_open_data.get(name, 'Default data'))()

        with patch("builtins.open", side_effect=open_side_effect):
            repo_config = self.repo_config_register._generate_repo_config_from_file(fake_file_path)
            assert repo_config["name"] == "ext-rhel8s-baseos"
            assert repo_config["repo_type"] == "rpm"
            assert repo_config["url"] == "https://cdn.redhat.com/content/dist/rhel8/8/x86_64/baseos/os"
            assert repo_config["proxy_url"] == "http://proxy.example.com:8080"
            assert repo_config["description"] == "RHEL 8 Base OS repo - Core Linux Engineering - base_url:rhel8s-x86_64"
            assert repo_config["ca_cert"] == "CA_CERT"
            assert repo_config["client_cert"] == "CLIENT_CERT_KEY"
            assert repo_config["client_key"] == "CLIENT_CERT_KEY"

    @patch("pulp_manager.app.services.repo_config_register.os.path.isfile")
    def test_generate_repo_config_from_file_internal_rpm(self, mock_isfile):
        """Tests the correct config is generated for an internal repo
        """

        mock_isfile.return_value = True
        fake_file_path = '/home/user/git/pulp_repo/internal/el7/repo.json'

        mock_open_data = {
            fake_file_path: json.dumps({
                "name": "internal-repo",
                "owner": "Core Linux Engineering",
                "description": "Internal repo",
                "repo_type": "internal",
                "content_repo_type": "rpm",
                "publish_latest": True,
                "base_url": "centos7-x86_64",
            })
        }

        def open_side_effect(name, mode=None):
            return mock_open(read_data=mock_open_data.get(name, 'Default data'))()

        with patch("builtins.open", side_effect=open_side_effect):
            repo_config = self.repo_config_register._generate_repo_config_from_file(fake_file_path)
            assert repo_config["name"] == "internal-repo"
            assert repo_config["repo_type"] == "rpm"
            assert repo_config["description"] == "Internal repo - Core Linux Engineering - base_url:centos7-x86_64"

    @patch("pulp_manager.app.services.repo_config_register.os.path.isfile")
    @patch("pulp_manager.app.services.repo_config_register.os.walk")
    def test_parse_repo_config_files_ok(self, mock_os_walk, mock_isfile):
        """Tests that _parse_repo_config_files contians the correct repos, based on if
        regex_include/exclude has been set/unset
        """

        mock_isfile.return_value = True
        mock_os_walk.return_value = [
            ('/fakedir/remote', ('el7', 'el8'), ()),
            ('/fakedir/remote/el7', (), ('el7repo.json',)),
            ('/fakedir/remote/el8', (), ('el8repo.json',)),
        ]

        mock_open_data = {
            "/fakedir/remote/el7/el7repo.json": json.dumps({
                "name": "el7repo",
                "url": "https://packages.microsoft.com/el7",
                "owner": "Core Linux Engineering",
                "description": "EL7 fake repo",
                "repo_type": "external",
                "content_repo_type": "rpm",
                "publish_latest": True,
                "base_url": "el7-x86_64"
            }),
            "/fakedir/remote/el8/el8repo.json": json.dumps({
                "name": "el8repo",
                "url": "https://packages.microsoft.com/el8",
                "owner": "Core Linux Engineering",
                "description": "EL8 fake repo",
                "repo_type": "external",
                "content_repo_type": "rpm",
                "publish_latest": True,
                "base_url": "el8-x86_64"
            }),
            "/fakedir/remote/global.json": json.dumps({
                "proxy": "http://proxy.example.com:8080"
            })
        }

        def open_side_effect(name, mode=None):
            return mock_open(read_data=mock_open_data.get(name, 'Default data'))()

        with patch("builtins.open", side_effect=open_side_effect):
            parsed_repo_configs = self.repo_config_register._parse_repo_config_files(
                "/fake_dir/", None, None
            )
            for repo_config in parsed_repo_configs:
                assert repo_config["name"] in ["ext-el7repo", "ext-el8repo"]

            parsed_repo_configs = self.repo_config_register._parse_repo_config_files(
                "/fake_dir/", "el7repo", None
            )
            assert len(parsed_repo_configs) == 1
            assert parsed_repo_configs[0]["name"] == "ext-el7repo"

            parsed_repo_configs = self.repo_config_register._parse_repo_config_files(
                "/fake_dir/", None, "el7repo"
            )
            assert len(parsed_repo_configs) == 1
            assert parsed_repo_configs[0]["name"] == "ext-el8repo"

    @patch("pulp_manager.app.services.repo_config_register.Repo.clone_from")
    def test_create_repos_from_git_config_fail(self, mock_clone_from):
        """Tests logic flow that if they are errors an exception is raised
        """

        mock_clone_from.side_effect = Exception("an error")


        with pytest.raises(Exception):
            self.repo_config_register.create_repos_from_git_config()

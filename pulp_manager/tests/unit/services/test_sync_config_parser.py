"""Tests for the sync config parser
"""

import pytest
import json
import os
from mock import patch, mock_open, MagicMock

from pulp_manager.app.database import session, engine
from pulp_manager.app.exceptions import PulpManagerPulpConfigError
from pulp_manager.app.models import RepoGroup, PulpServer, PulpServerRepoGroup
from pulp_manager.app.repositories import (
    PulpServerRepository, RepoGroupRepository, PulpServerRepoGroupRepository
)
from pulp_manager.app.services.sync_config_parser import (
    validate_schema, load_pulp_config, parse_config_file, PulpConfigParser
)

def test_validate_schema_pass():
    """Tests that a valid schema doesn't generate any exceptions
    """

    config = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            },
            "core-rpm.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "vault_service_account_mount": "service-accounts"
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }

    validate_schema(config)


def test_validate_schema_invalid_server():
    """Tests what when invalid config is given for a pulp server an exception is raised
    """

    config = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "vault_service_account_mount": "service-accounts"
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }

    with pytest.raises(PulpManagerPulpConfigError):
        validate_schema(config)


def test_validate_schema_invalid_credentials():
    """Tests what when invalid config is given for a credential an exception is raised
    """

    config = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "password": "password",
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }


    with pytest.raises(PulpManagerPulpConfigError):
        validate_schema(config)


def test_validate_schema_missing_credentials():
    """Tests that when credential name is missing an exception is raised
    """

    config = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "credentials": "example_credzzz",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "vault_service_account_mount": "service-accounts"
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }

    with pytest.raises(PulpManagerPulpConfigError):
        validate_schema(config)


def test_validate_schema_missing_repo_group():
    """Tests that when the repo group name is invalid an exception is raised
    """

    config = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repozzzzzz": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "vault_service_account_mount": "service-accounts"
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }

    with pytest.raises(PulpManagerPulpConfigError):
        validate_schema(config)


@patch("os.path.isfile")
def test_load_pulp_config(mock_isfile):
    """Tests that when a valid file yaml file is passed a dict is returned
    """

    mock_isfile.return_value = True

    def open_side_effect(name, mode=None):
        return mock_open(read_data=json.dumps({"key": "value"}))()

    with patch("builtins.open", side_effect=open_side_effect):
        result = load_pulp_config("test.yaml")
        assert isinstance(result, dict)


@patch("os.path.isfile")
def test_load_pulp_config_missing_file(mock_isfile):
    """Tests that when a path passed isn't a file an excpetion is raised
    """

    mock_isfile.return_value = False

    with pytest.raises(PulpManagerPulpConfigError):
        result = load_pulp_config("invalid.yaml")


@patch("pulp_manager.app.services.sync_config_parser.load_pulp_config")
def test_parse_config_file(mock_load_pulp_config):
    """Tests that with a valid config file parse_config_file loads correctly
    """

    mock_load_pulp_config.return_value = {
        "pulp_servers": {
            "pulpmast1.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            },
            "core-rpm.example.com": {
                "credentials": "example_creds",
                "repo_groups": {
                    "external_repos": {
                        "schedule": "0 0 * * *",
                        "max_concurrent_syncs": 2,
                        "max_runtime": "2h"
                    }
                }
            }
        },
        "credentials": {
            "example_creds": {
                "username": "test",
                "vault_service_account_mount": "service-accounts"
            }
        },
        "repo_groups": {
            "external_repos": {
                "regex_include": "^ext-"
            }
        }
    }

    result = parse_config_file("test.yaml")
    assert isinstance(result, dict)


class TestPulpConfigParser:
    """Carried out tests in the pulp config parser
    """

    def setup_method(self):
        """Ensure an instance of PulpConfigParser is avaialble for all tests
        """

        # Clear db before each run, so that generated sample data for these tests
        # is reset for each test, as these objects get manipulated each time
        self.db = session()
        pulp_server_repository = PulpServerRepository(self.db)
        pulp_server_repo_group_repository = PulpServerRepoGroupRepository(self.db)
        repo_group_repository = RepoGroupRepository(self.db)

        for pulp_server in pulp_server_repository.filter():
            pulp_server_repository.delete(pulp_server)

        for repo_group in repo_group_repository.filter():
            repo_group_repository.delete(repo_group)

        self.db.commit()


        self.pulpmast3 = pulp_server_repository.add(**{
            "name": "pulpmast3.example.com",
            "username": "username",
            "vault_service_account_mount": "service-accounts",
            "snapshot_supported": False,
            "max_concurrent_snapshots": None
        })

        self.pulpslav1 = pulp_server_repository.add(**{
            "name": "pulpslav1.example.com",
            "username": "username",
            "vault_service_account_mount": "service-accounts",
            "snapshot_supported": False,
            "max_concurrent_snapshots": None
        })

        self.repo_group1 = repo_group_repository.add(**{
            "name": "repo_group_1",
            "regex_include": "rg1"
        })

        self.repo_group2 = repo_group_repository.add(**{
            "name": "repo_group_2",
            "regex_exclude": "rg2"
        })

        self.repo_group3 = repo_group_repository.add(**{
            "name": "repo_group_3",
            "regex_exclude": "rg3"
        })

        self.pulpmast3_repo_group1 = pulp_server_repo_group_repository.add(**{
            "pulp_server": self.pulpmast3,
            "repo_group": self.repo_group1,
            "schedule": "0 0 * * *",
            "max_runtime": "6h",
            "max_concurrent_syncs": 2
        })

        self.pulpmast3_repo_group3 = pulp_server_repo_group_repository.add(**{
            "pulp_server": self.pulpmast3,
            "repo_group": self.repo_group3,
            "schedule": "0 0 * * *",
            "max_runtime": "6h",
            "max_concurrent_syncs": 2
        })

        self.db.commit()
        self.pulp_config_parser = PulpConfigParser(self.db)

    def teardown_method(self):
        """Ensure db connections are closed
        """

        self.db.close()
        engine.dispose()

    def test_get_existing_repo_groups(self):
        """Tests that a dict is returned where the key is the repo group name
        and the value is the matching repo group object
        """

        result = self.pulp_config_parser._get_existing_repo_groups()

        # _get_existing_repo_groups returns a dict where there are two keys pointing to the
        # same value. the first key is the name of the repo group and the second key is the ID
        # of the repo group
        for key in result:
            if isinstance(key, str):
                assert isinstance(result[key], RepoGroup)
                repo_group_id = result[key].id
                assert result[repo_group_id].name == key

    def test_calculate_repo_groups_to_add(self):
        """Tests that a list of dicts of repo groups to add is returned which contains
        repo groups that do no exist in the database
        """

        fake_existing_repo_groups = {
            "repo_group_1": RepoGroup(**{
                "id": 1,
                "name": "repo_group_1",
                "regex_include": "rg1"
            }),
            "repo_group_3": RepoGroup(**{
                "id": 3,
                "name": "repo_group_3",
                "regex_exclude": "rg3"
            })
        }

        fake_configured_repo_groups = {
            "repo_group_1": {"regex_include": "rg1_updates"},
            "repo_group_4": {"regex_exclude": "rg4"},
            "repo_group_5": {"regex_include": "rg5", "regex_exclude": "ex"},
        }

        result = self.pulp_config_parser._calculate_repo_groups_to_add(
            fake_existing_repo_groups, fake_configured_repo_groups
        )

        # looping over a list of dicts, as the _calculate_repo_groups_to_add method
        # generates a dict to carry out a bulk add of repo groups
        for repo_group_to_add in result:
            name = repo_group_to_add["name"]
            assert name  not in fake_existing_repo_groups

            # check correct regex include/exclude values have been copied
            for configured_prop_key, configured_prop_value in fake_configured_repo_groups[name].items():
                assert configured_prop_key in repo_group_to_add
                assert repo_group_to_add[configured_prop_key] == configured_prop_value

    def test_calculate_repo_groups_to_remove(self):
        """Tests that a list of entities is returned for the repo groups to be removed. Checks
        the correct repo groups are in the list
        """

        fake_existing_repo_groups = {
            "repo_group_1": RepoGroup(**{
                "id": 1,
                "name": "repo_group_1",
                "regex_include": "rg1"
            }),
            "repo_group_3": RepoGroup(**{
                "id": 3,
                "name": "repo_group_3",
                "regex_exclude": "rg3"
            })
        }

        fake_configured_repo_groups = {
            "repo_group_1": {"regex_include": "rg1_updates"},
            "repo_group_4": {"regex_exclude": "rg4"},
            "repo_group_5": {"regex_include": "rg5", "regex_exclude": "ex"},
        }

        result = self.pulp_config_parser._calculate_repo_groups_to_remove(
            fake_existing_repo_groups, fake_configured_repo_groups
        )

        for repo_group in result:
            assert repo_group.name not in fake_configured_repo_groups

    def test_calculate_repo_groups_to_update(self):
        """Tests that a list of dicts is returned of only repo groups to update. Checks
        that only values that need updating are returned
        """

        fake_existing_repo_groups = {
            "repo_group_1": RepoGroup(**{
                "id": 1,
                "name": "repo_group_1",
                "regex_include": "rg1"
            }),
            "repo_group_3": RepoGroup(**{
                "id": 3,
                "name": "repo_group_3",
                "regex_exclude": "rg3"
            })
        }

        fake_configured_repo_groups = {
            "repo_group_1": {"regex_include": "rg1_updates"},
            "repo_group_4": {"regex_exclude": "rg4"},
            "repo_group_5": {"regex_include": "rg5", "regex_exclude": "ex"},
        }

        result = self.pulp_config_parser._calculate_repo_groups_to_update(
            fake_existing_repo_groups, fake_configured_repo_groups
        )

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["regex_include"] == "rg1_updates"
        assert "name" not in result[0]
        assert "regex_exclude" not in result[0]

    def test_process_repo_groups(self):
        """Tests that repo groups are added/updated/deleted correctly from the DB.
        Test replaces the internal repositories with magic mocks to count the number
        of times  method was called
        """

        fake_configured_repo_groups = {
            "repo_group_1": {"regex_include": "rg1_updates"},
            "repo_group_4": {"regex_exclude": "rg4"},
            "repo_group_5": {"regex_include": "rg5", "regex_exclude": "ex"},
        }

        result = self.pulp_config_parser._process_repo_groups(fake_configured_repo_groups)
        # Expect 6 items in the list because the fact the dict contains two refferences
        # to the repo groups. One via the repo group name and the other via the repo group ID
        assert len(result.keys()) == 6
        for repo_group_name in result.keys():
            if isinstance(repo_group_name, str):
                assert repo_group_name in fake_configured_repo_groups

    def test_get_existing_pulp_servers(self):
        """Tests that a dict of pulp servers is returned where the key is the name
        of a pulp server in the db and the value is the pulp server entity
        """

        result = self.pulp_config_parser._get_existing_pulp_servers()
        assert len(result["pulpmast3.example.com"].repo_groups) == 2
        assert len(result["pulpslav1.example.com"].repo_groups) == 0

    def test_add_pulp_servers(self):
        """Tests that a pulp server gets added to the DB with the correct repo group
        """

        # Can ignore adding repo group regex_incldue/exclude config as the repo_groups argument
        # to _add_pulp_server contains the repo_groups that exist in the db which already
        # contains this information as the processing of repo groups takes place before
        # pulp server
        fake_config = {
            "pulp_servers": {
                "pulpslav3.example.com": {
                    "credentials": "example_new",
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_concurrent_syncs": 2,
                            "max_runtime": "2h"
                        }
                    }
                }
            },
            "credentials": {
                "example_new": {
                    "username": "new-svc-account",
                    "vault_service_account_mount": "service-accounts"
                }
            }
        }

        # Use the pulp_config_parser that contains a mock db and repo group info
        # to load the exisitng repo groups in the correct format
        fake_repo_groups_db = self.pulp_config_parser._get_existing_repo_groups()
        self.pulp_config_parser._add_pulp_servers(fake_config)

        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        assert "pulpslav3.example.com" in existing_pulp_servers
        assert existing_pulp_servers["pulpslav3.example.com"].username == "new-svc-account"
        assert existing_pulp_servers["pulpslav3.example.com"].vault_service_account_mount == "service-accounts"

    def test_update_pulp_server(self):
        """Tests that the correct updates are made to a pulp server from the config dict
        """

        pulp_server_updates = {
            "pulp_server": self.pulpmast3,
            "pulp_server_config": {
                "username": "username-updated"
            },
            "repo_groups_to_add": [{
                "pulp_server_id": self.pulpmast3.id,
                "repo_group_id": self.repo_group2.id,
                "schedule": "0 2 * * *",
                "max_concurrent_syncs": 3,
                "max_runtime": "3h"
            }],
            "repo_groups_to_update": [{
                "pulp_server_id": self.pulpmast3.id,
                "repo_group_id": self.repo_group1.id,
                "max_runtime": "3h"
            }],
            "repo_groups_to_remove": [
                self.pulpmast3_repo_group3
            ]
        }

        self.pulp_config_parser._update_pulp_server(pulp_server_updates)
        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        pulp_server = existing_pulp_servers["pulpmast3.example.com"]
        assert pulp_server.username == "username-updated"
        assert len(pulp_server.repo_groups) == 2

        # Refresh the SQL alchemy object to get the updates that have been made to it
        self.db.refresh(pulp_server)

        found_added_repo_group = False
        repo_group_updated = False
        for repo_group in pulp_server.repo_groups:
            if (repo_group.pulp_server_id == self.pulpmast3.id
                    and repo_group.repo_group_id == self.repo_group2.id):
                found_added_repo_group = True
            if (repo_group.pulp_server_id == self.pulpmast3.id
                    and repo_group.repo_group_id == self.repo_group1.id
                    and repo_group.max_runtime == "3h"):
                repo_group_updated = True

        assert found_added_repo_group == True
        assert repo_group_updated == True

    def test_remove_pulp_servers(self):
        """Tests that the correct pulp servers are removed from the DB
        """

        pulp_servers_to_remove = [self.pulpslav1]

        pulp_server_count_before_delete = len(self.pulp_config_parser._get_existing_pulp_servers())

        self.pulp_config_parser._remove_pulp_servers(pulp_servers_to_remove)
        pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        assert len(pulp_servers) + 1 == pulp_server_count_before_delete

        for pulp_server_name in pulp_servers:
            assert pulp_servers[pulp_server_name].id != 2

    def test_calculate_pulp_server_repo_groups_to_add(self):
        """Tests that a list is returned that contains config only for repo groups that
        need to be added to the pulp server
        """

        # Minimal config to make the required test work
        fake_config = {
            "pulp_servers": {
                "pulpslav1.example.com": {
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2,
                            "pulp_master": "pulpmast3.example.com"
                        }
                    }
                }
            }
        }

        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()
        repo_groups_to_add = self.pulp_config_parser._calculate_pulp_server_repo_groups_to_add(
            existing_pulp_servers["pulpslav1.example.com"],
            existing_repo_groups,
            fake_config,
            existing_pulp_servers
        )

        assert len(repo_groups_to_add) == 1
        assert repo_groups_to_add[0]["pulp_server_id"] == self.pulpslav1.id
        assert repo_groups_to_add[0]["repo_group_id"] == self.repo_group1.id
        assert repo_groups_to_add[0]["schedule"] == "0 0 * * *"
        assert repo_groups_to_add[0]["max_runtime"] == "3h"
        assert repo_groups_to_add[0]["max_concurrent_syncs"] == 2
        assert repo_groups_to_add[0]["pulp_master_id"] == self.pulpmast3.id

    def test_calculate_pulp_server_repo_groups_to_update(self):
        """Checks that a list is returned that contains on the fields that need to be updated for
        the given pulp server repo groups
        """

        # repo_group_3 is in because the mocked sample data has two repo groups assigned
        # to pulpmast3.example.com. repo_group_3 needs to have no changes from the mocked
        # data so that it isn't marked as a repo group for update
        fake_config = {
            "pulp_servers": {
                "pulpmast3.example.com": {
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        },
                        "repo_group_3": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "6h",
                            "max_concurrent_syncs": 2
                        }
                    }
                }
            }
        }

        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()
        repo_groups_to_update = self.pulp_config_parser._calculate_pulp_server_repo_groups_to_update(
            existing_pulp_servers["pulpmast3.example.com"],
            existing_repo_groups,
            fake_config,
            existing_pulp_servers
        )

        assert len(repo_groups_to_update) == 1
        assert repo_groups_to_update[0]["pulp_server_id"] == self.pulpmast3.id
        assert repo_groups_to_update[0]["repo_group_id"] == self.repo_group1.id
        assert repo_groups_to_update[0]["max_runtime"] == "3h"
        # Check fields we are not updating have not been added to the dict
        assert "schedule" not in repo_groups_to_update[0]
        assert "max_concurrent_syncs" not in repo_groups_to_update[0]

    def test_calculate_pulp_server_repo_groups_to_remove(self):
        """Checks that the correct PulpServerRepoGroup entites are returned to be removed
        from the database
        """

        # minimal fake config
        fake_config = {
            "pulp_servers": {
                "pulpmast3.example.com": {
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        }
                    }
                }
            }
        }

        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()

        repo_groups_to_remove = self.pulp_config_parser._calculate_pulp_server_repo_groups_to_remove(
            existing_pulp_servers["pulpmast3.example.com"],
            existing_repo_groups,
            fake_config
        )

        assert len(repo_groups_to_remove) == 1
        assert repo_groups_to_remove[0].repo_group_id == self.repo_group3.id

    def test_calculate_pulp_server_updates(self):
        """Checks that only pulp servers, which required an update have config returned
        """

        fake_config = {
            "pulp_servers": {
                "pulpmast3.example.com": {
                    "credentials": "example",
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        },
                        "repo_group_2": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        }
                    }
                },
                "pulpslav1.example.com": {
                    "credentials": "example",
                    "repo_groups": {}
                }
            },
            "credentials": {
                "example": {
                    "username": "username",
                    "vault_service_account_mount": "service-accounts"
                }
            }
        }

        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()

        pulp_servers = []
        for key, value in existing_pulp_servers.items():
            pulp_servers.append(value)

        pulp_servers_to_update = self.pulp_config_parser._calculate_pulp_server_updates(
            pulp_servers, existing_repo_groups, fake_config, existing_pulp_servers
        )

        assert len(pulp_servers_to_update) == 1
        assert pulp_servers_to_update[0]["pulp_server"].name == "pulpmast3.example.com"
        assert len(pulp_servers_to_update[0]["pulp_server_config"]) == 0
        assert len(pulp_servers_to_update[0]["repo_groups_to_add"]) == 1
        assert pulp_servers_to_update[0]["repo_groups_to_add"][0]["repo_group_id"] not in [1, 3]
        assert len(pulp_servers_to_update[0]["repo_groups_to_update"]) == 1
        assert len(pulp_servers_to_update[0]["repo_groups_to_remove"]) == 1

    def test_calculate_pulp_servers_to_remove(self):
        """Tests that from a list of pulp servers and loaded config, the correct
        Pulp Server entities are returned to be removed from the DB
        """

        fake_config = {
            "pulp_servers": {
                "pulpmast3.example.com": {}
            }
        }

        pulp_servers = []
        existing_pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()

        for key, value in existing_pulp_servers.items():
            pulp_servers.append(value)

        pulp_servers_to_remove = self.pulp_config_parser._calculate_pulp_servers_to_remove(
            pulp_servers, fake_config
        )

        assert len(pulp_servers_to_remove) == 1
        assert pulp_servers_to_remove[0].name == "pulpslav1.example.com"

    def test_process_pulp_servers(self):
        """Tests expected updates are made to the pulp server config in the DB
        """

        fake_config = {
            "pulp_servers": {
                "pulpmast3.example.com": {
                    "credentials": "example",
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        },
                        "repo_group_2": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        }
                    }
                },
                "pulpslav2.example.com": {
                    "credentials": "example",
                    "repo_groups": {
                        "repo_group_2": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "6h",
                            "max_concurrent_syncs": 4
                        }
                    }
                }
            },
            "credentials": {
                "example": {
                    "username": "username",
                    "vault_service_account_mount": "service-accounts"
                }
            },
            "repo_groups": {
                "repo_group_1": {
                    "regex_include": "rg1"
                },
                "repo_group_2": {
                    "regex_exclude": "rg2"
                }
            }
        }

        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()
        self.pulp_config_parser._process_pulp_servers(fake_config, existing_repo_groups)


        pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        repo_groups = self.pulp_config_parser._get_existing_repo_groups()

        assert len(pulp_servers) == 2
        assert "pulpmast3.example.com" in pulp_servers
        assert "pulpslav2.example.com" in pulp_servers

    @patch("pulp_manager.app.services.sync_config_parser.parse_config_file")
    def test_load_config(self, mock_parse_config_file):
        """Tests db is updated correctly based on differences from config that is loaded
        """

        mock_parse_config_file.return_value = {
            "pulp_servers": {
                "pulpmast3.example.com": {
                    "credentials": "example",
                    "repo_groups": {
                        "repo_group_1": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        },
                        "repo_group_2": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "3h",
                            "max_concurrent_syncs": 2
                        }
                    }
                },
                "pulpslav2.example.com": {
                    "credentials": "example",
                    "repo_groups": {
                        "repo_group_2": {
                            "schedule": "0 0 * * *",
                            "max_runtime": "6h",
                            "max_concurrent_syncs": 4
                        }
                    }
                }
            },
            "credentials": {
                "example": {
                    "username": "username",
                    "vault_service_account_mount": "service-accounts"
                }
            },
            "repo_groups": {
                "repo_group_1": {
                    "regex_include": "rg1"
                },
                "repo_group_2": {
                    "regex_exclude": "rg2"
                }
            }
        }

        existing_repo_groups = self.pulp_config_parser._get_existing_repo_groups()
        self.pulp_config_parser.load_config("fake_file.yml")


        pulp_servers = self.pulp_config_parser._get_existing_pulp_servers()
        repo_groups = self.pulp_config_parser._get_existing_repo_groups()

        assert len(pulp_servers) == 2
        assert "pulpmast3.example.com" in pulp_servers
        assert "pulpslav2.example.com" in pulp_servers
        assert len(repo_groups) == 4 # Due to two differnt keys pointing to same entity by id and name
        assert "repo_group_1" in repo_groups
        assert "repo_group_2" in repo_groups

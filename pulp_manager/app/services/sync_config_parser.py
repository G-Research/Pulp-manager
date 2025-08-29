"""Used for parsing repo sync config
"""

import os
from typing import List
import yaml
from cerberus import Validator
from sqlalchemy.orm import Session
from pulp_manager.app.utils import log
from pulp_manager.app.exceptions import PulpManagerPulpConfigError
from pulp_manager.app.models import PulpServer
from pulp_manager.app.services.base import PulpManagerDBService
from pulp_manager.app.repositories import (
    PulpServerRepository, PulpServerRepoGroupRepository, RepoGroupRepository
)


def validate_schema(config: dict):
    """Validates the given config dict checking for expected fields.
    Schema error is raised if the config is not valid. Won't catch dodgy
    cron syntaxes or max_runtime values, but gets enough of the config validated
    """

    schema = {
        "pulp_servers": {
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[a-z0-9\\.\\-_]+(:[0-9]+)?$"},
            "valuesrules": {
                "type": "dict",
                "schema": {
                    "credentials": {"type": "string", "required": True},
                    "repo_config_registration": {
                        "type": "dict",
                        "required": False,
                        "keysrules": {"type": "string", "regex": "^[a-z][a-z0-9\\-_]+$"},
                        "schema": {
                            "schedule": {"type": "string", "required": True},
                            "max_runtime": {"type": "string", "required": True},
                            "regex_include": {"type": "string", "required": False},
                            "regex_exclude": {"type": "string", "required": False}
                        }
                    },
                    "repo_groups": {
                        "type": "dict",
                        "required": True,
                        "keysrules": {"type": "string", "regex": "^[a-z][a-z0-9\\-_]+$"},
                        "valuesrules": {
                            "type": "dict",
                            "schema": {
                                "schedule": {"type": "string", "required": False},
                                "max_concurrent_syncs": {"type": "integer", "required": True},
                                "max_runtime": {"type": "string", "required": True},
                                "pulp_master": {"type": "string", "required": False},
                            }
                        }
                    },
                    "snapshot_support": {
                        "type": "dict",
                        "required": False,
                        "keysrules": {"type": "string", "regex": "^[a-z][a-z0-9\\-_]+$"},
                        "schema": {
                            "max_concurrent_snapshots": {"type": "integer", "required": True}
                        }
                    }
                }
            }
        },
        "credentials": {
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[a-z0-9]+[a-z\\-_]+$"},
            "valuesrules": {
                "type": "dict",
                "schema": {
                    "username": {"type": "string", "required": True},
                    "vault_service_account_mount": {"type": "string", "required": True}
                }
            }
        },
        "repo_groups": {
            "type": "dict",
            "keysrules": {"type": "string", "regex": "^[a-z][a-z\\-_]+$"},
            "valuesrules": {
                "type": "dict",
                "schema": {
                    "regex_include": {"type": "string", "required": False},
                    "regex_exclude": {"type": "string", "required": False}
                }
            }
        }
    }


    validator = Validator(schema)
    if not validator.validate(config):
        log.error("pulp config failed validation")
        log.error(validator.errors)
        raise PulpManagerPulpConfigError(validator.errors)

    config_errors = []

    # Check the crednetials groups exist
    for pulp_server in config['pulp_servers']:
        for repo_group in config['pulp_servers'][pulp_server]['repo_groups']:
            if ("pulp_primary" in repo_group
                    and repo_group["pulp_primary"] not in config['pulp_servers']):
                config_errors.append(
                    f"pulp primary {repo_group['pulp_primary']} missing"
                )
            if repo_group not in config['repo_groups']:
                config_errors.append(
                    f"{repo_group} missing from repo_groups section, required for {pulp_server}"
                )

        pulp_credentials = config['pulp_servers'][pulp_server]['credentials']
        if pulp_credentials not in config['credentials']:
            config_errors.append(
                f"{pulp_credentials} missing from credentials section, required for {pulp_server}"
            )

    if len(config_errors) > 0:
        message = f"pulp config errors: {', '.join(config_errors)}"
        log.error(message)
        raise PulpManagerPulpConfigError(message)


def load_pulp_config(config_path: str):
    """Loads the config from the given filepath
    """

    if not os.path.isfile(config_path):
        log.error(f"{config_path} is not a file")
        raise PulpManagerPulpConfigError(f"{config_path} is not a file")

    #pylint: disable=unspecified-encoding
    with open(config_path, 'r') as config_file:
        return yaml.safe_load(config_file.read())


def parse_config_file(config_path: str):
    """Parses the config file and returns a dict, containg the specified options
    """

    log.info(f"parsing pulp config file {config_path}")
    config = load_pulp_config(config_path)
    validate_schema(config)
    log.info(f"parsing of {config_path} was successful")
    return config


class PulpConfigParser(PulpManagerDBService):
    """Used for parsing pulp config and sets up scheduled jobs
    that eventually get picked up by RQ workers
    """

    # pylint: disable = super-init-not-called
    def __init__(self, db: Session):
        """Constructor
        :param db: DB session to use
        :type db: Session
        :param model: Model that the repository is responsbile for
        :type model: object
        """

        self.db = db
        self.pulp_server_crud = PulpServerRepository(db)
        self.repo_group_crud = RepoGroupRepository(db)
        self.pulp_server_repo_group_crud = PulpServerRepoGroupRepository(db)

    def _get_existing_repo_groups(self):
        """Returns existing repo groups in a dict. Model is added with two
        differnent keys, one being repo group name and the other being hte id
        """

        log.info("retrieving existing repo groups")
        repo_groups = self.repo_group_crud.filter()
        repo_groups_dict = {}
        for repo_group in repo_groups:
            log.debug(f"found repo group {repo_group.name} with id {repo_group.id}")
            repo_groups_dict[repo_group.name] = repo_group
            repo_groups_dict[repo_group.id] = repo_group
        return repo_groups_dict

    def _calculate_repo_groups_to_add(self, existing_repo_groups: dict,
            configured_repo_groups: dict):
        """Returns a list of dicts of repo groups to add, based on exsiting repo groups
        and configured repo groups
        :param existing_repo_groups: dict of repo groups, key is repo group name, and value is
                                     db model
        :type existing_repo_groups: dict
        :param configured_repo_groups: dict of repo group confgurations that came from pulp
                                       schedule config. Key is repo group name, and value
                                       is the dict config loaded from ymal config file
        :return: list
        """

        repo_groups_to_add = []

        repo_group_names_to_add = list(
            set(configured_repo_groups.keys()) - set(existing_repo_groups.keys())
        )
        log.info(f"repo groups to add {','.join(repo_group_names_to_add)}")

        for repo_group in repo_group_names_to_add:
            # create a temp repo group so we can add th e name key
            temp_repo_group = dict(configured_repo_groups[repo_group])
            temp_repo_group['name'] = repo_group
            repo_groups_to_add.append(temp_repo_group)

        return repo_groups_to_add

    def _calculate_repo_groups_to_remove(self, existing_repo_groups: dict,
            configured_repo_groups: dict):
        """Calculates the remove groups that should be removed from the db. Returns a list
        of repo group entities that need to be removed
        :param existing_repo_groups: dict of repo groups, key is repo group name, and value is
                                     db model
        :type existing_repo_groups: dict
        :param configured_repo_groups: dict of repo group confgurations that came from pulp
                                       schedule config. Key is repo group name, and value
                                       is the dict config loaded from ymal config file
        :return: list
        """

        repo_groups_to_remove = []
        existing_repo_groups_names = [
            name for name in existing_repo_groups.keys() if isinstance(name, str)
        ]

        repo_group_names_to_remove = list(
            set(existing_repo_groups_names) - set(configured_repo_groups.keys())
        )
        log.info(f"repo groups to remove {','.join(repo_group_names_to_remove)}")

        for repo_group in repo_group_names_to_remove:
            repo_groups_to_remove.append(existing_repo_groups[repo_group])

        return repo_groups_to_remove

    def _calculate_repo_groups_to_update(self, existing_repo_groups: dict,
            configured_repo_groups: dict):
        """Checks if any repo groups need to be updated and if so returns
        a list of dicts containg the fileds that need to be updated
        for each repo group
        :param existing_repo_groups: dict of repo groups, key is repo group name, and value is
                                     db model
        :type existing_repo_groups: dict
        :param configured_repo_groups: dict of repo group confgurations that came from pulp
                                       schedule config. Key is repo group name, and value
                                       is the dict config loaded from ymal config file
        :return: list
        """

        log.info("calculating repo groups to update")
        repo_groups_to_update = []
        # Gets the repo group names that exsit in the db and the config file
        repo_group_name_intersection = list(
            set(existing_repo_groups.keys()).intersection(configured_repo_groups.keys())
        )

        for repo_group in repo_group_name_intersection:
            update_config = {}
            for key, value in configured_repo_groups[repo_group].items():
                # Check the value on the model matches that set from the config
                # file. If it doesn't add that to our update_config dict
                if value != getattr(existing_repo_groups[repo_group], key):
                    update_config[key] = value

                if len(update_config) > 0:
                    log.info(f"repo group {repo_group} needs to be updated in teh db")
                    update_config['id'] = existing_repo_groups[repo_group].id
                    repo_groups_to_update.append(update_config)

        return repo_groups_to_update


    def _process_repo_groups(self, repo_group_configs: dict):
        """Calculates the changes that needed to be made to the db to create/update/delete
        the repo groups, and applies them. Changes are made in one transaction
        :param repo_group_configs: dict contains the repo group configs. key is repo group name
                                   and value is the settings for the repo group
                                   (regex_include/exclude)
        :type repo_group_configs: dict
        """

        log.info("Calculating repo group db changes")
        existing_repo_groups = self._get_existing_repo_groups()

        repo_groups_to_add = self._calculate_repo_groups_to_add(
            existing_repo_groups, repo_group_configs
        )
        repo_groups_to_update = self._calculate_repo_groups_to_update(
            existing_repo_groups, repo_group_configs
        )
        repo_groups_to_remove = self._calculate_repo_groups_to_remove(
            existing_repo_groups, repo_group_configs
        )

        if(len(repo_groups_to_add) > 0 or len(repo_groups_to_update) > 0 or
                len(repo_groups_to_remove) > 0):

            try:
                if len(repo_groups_to_add) > 0:
                    self.repo_group_crud.bulk_add(repo_groups_to_add)
                if len(repo_groups_to_update) > 0:
                    self.repo_group_crud.bulk_update(repo_groups_to_update)
                if len(repo_groups_to_remove) > 0:
                    for repo_group in repo_groups_to_remove:
                        self.repo_group_crud.delete(repo_group)
                self.db.commit()
                existing_repo_groups = self._get_existing_repo_groups()
            except Exception:
                log.exception("An error occured updating repo groups")
                self.db.rollback()
                raise

        return existing_repo_groups

    def _get_existing_pulp_servers(self):
        """Returns existing pulp server in a dict. Key is pulp server name
        and the value is a db model
        """

        log.info("retrieving existing pulp servers")
        # Load the repos known for the pulp server to save another db call
        # later when sorting updates/editions of repos
        pulp_servers = self.pulp_server_crud.get_pulp_server_with_repo_groups()
        pulp_servers_dict = {}
        for pulp_server in pulp_servers:
            log.debug(f"found pulp server {pulp_server.name} with id {pulp_server.id}")
            pulp_servers_dict[pulp_server.name] = pulp_server
        return pulp_servers_dict

    def _get_pulp_server_entity_config(self, pulp_server_name, pulp_server_config: dict,
            credentials_config: dict):
        """Given config for a pulp server and credentials, a new dict is returned, containing
        key value pairs that are valid for creating/updating a pulp server entity.

        :param pulp_server_name: name of the pulp server the entity config is being created for
        :type pulp_server_name: str
        :param pulp_server_config: configuration of the pulp server as defined in the yml
                                   file for repo config registration/repo group and snapshot
                                   support
        :type pulp_server_config: dict
        :param credentials_config: configuration of the credentials defined in the pulp
                                   yml that matches the values for credentials
                                   on the pulp server configuration section
        :type credentials_config: dict
        :return: dict
        """
        if not ("password" in credentials_config or
                "vault_service_account_mount" in credentials_config):
            raise ValueError(
                "Either 'password' or 'vault_service_account_mount' must be provided"
                " in credentials_config"
            )


        #pylint: disable=line-too-long
        pulp_server_entity_config = {
            "name": pulp_server_name,
            "username": credentials_config["username"],
           "vault_service_account_mount": credentials_config.get("vault_service_account_mount"),
            "snapshot_supported": "snapshot_support" in pulp_server_config,
            "max_concurrent_snapshots": pulp_server_config["snapshot_support"]["max_concurrent_snapshots"] \
                     if "snapshot_support" in pulp_server_config else None
        }

        if "repo_config_registration" in pulp_server_config:
            repo_registration = pulp_server_config["repo_config_registration"]
            pulp_server_entity_config.update({
                "repo_config_registration_schedule": repo_registration["schedule"],
                "repo_config_registration_max_runtime": repo_registration["max_runtime"],
                "repo_config_registration_regex_include": repo_registration.get("regex_include", None),
                "repo_config_registration_regex_exclude": repo_registration.get("regex_exclude", None)
            })

        return pulp_server_entity_config

    def _add_pulp_servers(self, config: dict):
        """Adds any missing pulp servers and returns an updated list

        :param pulp_servers: List of pulp server names that were defined in config
        :type pulp_servers: List[str]
        :param config: dict containing the yaml loaded config about pulp syncs
        :type config: dict
        :return: List[PulpServer]
        """

        pulp_servers_in_db = self._get_existing_pulp_servers()
        missing_pulp_servers = []
        for pulp_server_name in config["pulp_servers"]:
            if pulp_server_name not in pulp_servers_in_db:
                missing_pulp_servers.append(pulp_server_name)

        if len(missing_pulp_servers) == 0:
            return pulp_servers_in_db

        try:
            for pulp_server_name in missing_pulp_servers:
                log.info(f"adding pulp server {pulp_server_name}")

                pulp_server_config = config["pulp_servers"][pulp_server_name]
                credentials_config = config["credentials"][pulp_server_config["credentials"]]
                pulp_server_entity_config = self._get_pulp_server_entity_config(
                    pulp_server_name, pulp_server_config, credentials_config
                )

                self.pulp_server_crud.add(**pulp_server_entity_config)
                self.db.flush()
            self.db.commit()
        except Exception:
            log.exception("error adding pulp server")
            self.db.rollback()
            raise

        pulp_servers_in_db = self._get_existing_pulp_servers()
        return pulp_servers_in_db

    def _update_pulp_server(self, pulp_server_updates: dict):
        """Makes the required updates to a pulp server. All change are made in one transaction.
        pulp_server_updates is a dict with the following keys:
            - pulp_server: pulp server object in the DB to updated
            - pulp_server_config: config for the pulp server to be update
            - repo_groups_to_add: List of dicts containing the repo groups to add
            - repo_groups_to_update: List of dicts containg repo group config to update
            - repo_groups_to_remove: List of PulpServerRepoGroup which should be removed
        :param pulp_server_updates: Dict containg the updates required for the pulp server
        :type pulp_server_updates: dict
        """

        try:
            pulp_server = pulp_server_updates["pulp_server"]
            log.info(f"making updates for {pulp_server.name}")

            if len(pulp_server_updates["pulp_server_config"]) > 0:
                self.pulp_server_crud.update(
                    pulp_server, **pulp_server_updates["pulp_server_config"]
                )

            if len(pulp_server_updates["repo_groups_to_add"]) > 0:
                self.pulp_server_repo_group_crud.bulk_add(
                    pulp_server_updates["repo_groups_to_add"]
            )

            if len(pulp_server_updates["repo_groups_to_update"]) > 0:
                self.pulp_server_repo_group_crud.bulk_update(
                    pulp_server_updates["repo_groups_to_update"]
                )

            for repo_group in pulp_server_updates["repo_groups_to_remove"]:
                self.pulp_server_repo_group_crud.delete(repo_group)

            self.db.commit()
        except Exception:
            log.exception(f"Error updating pulp server {pulp_server_updates['pulp_server'].name}")
            self.db.rollback()
            raise

    def _remove_pulp_servers(self, pulp_servers: List[PulpServer]):
        """Removes the specified pulp server from the db. All Pulp Server are removed in
        one transaction
        :param pulp_server: List of Pulpserver entities to remove from the DB
        :type pulp_server: str
        """

        try:
            log.info("Removing pulp servers no longer needed from the db")
            for pulp_server in pulp_servers:
                self.pulp_server_crud.delete(pulp_server)

            self.db.commit()
        except Exception:
            log.exception("Failed to remove pulp servers from the db")
            self.db.rollback()
            raise

    def _calculate_pulp_server_repo_groups_to_add(self, pulp_server: PulpServer,
            repo_groups: dict, config: dict, existing_pulp_servers: dict):
        """Calculates the repo groups that need to be added to a pulp server
        and returns a list of dicts with the options needed. 
        :param pulp_server: Existing pulp server entity in the DB
        :type pulp_server: PulpServer
        :param repo_groups: Dict of repo groups that map to entities in the DB.
                            Key is the repo group name
        :type repo_groups: dict
        :param config: dict of config which can be used for bulk updates of PulpServerRepoGroup
        :type config: dict
        :param existing_pulp_servers: dict of pulp servers that exist in the db. Key is name
                                      of the pulp server, value is the PulpServer entity
        :type existing_pulp_servers: dict
        :return list
        """

        log.info(f"calculating repo groups to add to {pulp_server.name}")
        repo_groups_to_add = []
        # List of repo group IDs already associated with the plp server
        pulp_repo_group_ids = [
            repo_group.repo_group_id for repo_group in pulp_server.repo_groups
        ]

        configured_repo_groups = config["pulp_servers"][pulp_server.name]["repo_groups"]
        for repo_group_name in configured_repo_groups:
            repo_group_config = configured_repo_groups[repo_group_name]
            repo_group_id = repo_groups[repo_group_name].id
            pulp_master_id = None
            if "pulp_master" in repo_group_config:
                pulp_master_id = existing_pulp_servers[repo_group_config["pulp_master"]].id

            if repo_group_id not in pulp_repo_group_ids:
                temp = dict(repo_group_config)
                temp["pulp_server_id"] = pulp_server.id
                temp["repo_group_id"] = repo_group_id
                if pulp_master_id is not None:
                    del temp["pulp_master"]
                    temp["pulp_master_id"] = pulp_master_id
                repo_groups_to_add.append(temp)

        log.info(f"{len(repo_groups_to_add)} repo groups need adding to {pulp_server.name}")
        return repo_groups_to_add


    def _calculate_pulp_server_repo_groups_to_update(self, pulp_server: PulpServer,
            repo_groups: dict, config: dict, existing_pulp_servers: dict):
        """Calculates the updates that are required to a PulpServerRepoGroup. Returns
        a list of dicts which contains the fileds that need to be updated for each
        repo group
        :param pulp_server: PulpServer entity in the database
        :type pulp_server: PulpServer
        :param repo_groups: Dict of repo groups that map to entities in the DB.
                            key can either be id or the name
        :type repo_groups: dict
        :param config: dict of config which can be used for bulk updates of PulpServerRepoGroup
        :type config: dict
        :param existing_pulp_servers: dict of pulp servers that exist in the db. Key is name
                                      of the pulp server, value is the PulpServer entity
        :type existing_pulp_servers: dict
        :return: list
        """

        log.info(f"calculating repo groups that need an update on {pulp_server.name}")
        repo_groups_to_update = []
        configured_repo_groups = config["pulp_servers"][pulp_server.name]["repo_groups"]

        for repo_group in pulp_server.repo_groups:
            # This is here for the fake repository as it doesn't handle cascade deletes
            if repo_group.repo_group_id not in repo_groups:
                continue

            repo_group_name = repo_groups[repo_group.repo_group_id].name
            if repo_group_name not in configured_repo_groups:
                continue

            repo_group_config = dict(configured_repo_groups[repo_group_name])
            pulp_master_id = None
            if "pulp_master" in repo_group_config:
                pulp_master_id = existing_pulp_servers[repo_group_config["pulp_master"]].id
                repo_group_config["pulp_master_id"] = pulp_master_id

            repo_group_updates = {}

            for key, value in repo_group_config.items():
                if getattr(repo_group, key) != value:
                    repo_group_updates[key] = value

            if len(repo_group_updates) > 0:
                repo_group_updates["pulp_server_id"] = pulp_server.id
                repo_group_updates["repo_group_id"] = repo_group.repo_group_id
                repo_groups_to_update.append(repo_group_updates)

        log.info(f"{len(repo_groups_to_update)} need updating on {pulp_server.name}")
        return repo_groups_to_update

    def _calculate_pulp_server_repo_groups_to_remove(self, pulp_server: PulpServer,
            repo_groups: dict, config: dict):
        """Calculates the repo groups that need t obe removed from a pulp server.
        Returns a list PulpServerRepoGroup models to be removed
        :param pulp_server: PulpServer database model to evaluate
        :type pulp_server: PulpServer
        :param repo_groups: Dict of repo groups that map to entities in the DB.
                            key can either be id or the name
        :type repo_groups: dict
        :param config: dict of config which can be used for bulk updates of PulpServerRepoGroup
        :type config: dict
        :return: list
        """

        log.info(f"calculating repo groups to remove on {pulp_server.name}")
        repo_groups_to_remove = []
        # IDs that are expected to be assigned to the pulp server based on the parsed config file
        repo_group_expected_ids = []

        for repo_group_name in config["pulp_servers"][pulp_server.name]["repo_groups"]:
            repo_group_expected_ids.append(repo_groups[repo_group_name].id)

        for repo_group in pulp_server.repo_groups:
            if repo_group.repo_group_id not in repo_group_expected_ids:
                repo_groups_to_remove.append(repo_group)

        log.info(f"{len(repo_groups_to_remove)} need to be removed from {pulp_server.name}")
        return repo_groups_to_remove

    # pylint: disable=line-too-long
    def _calculate_pulp_server_updates(self, pulp_servers: List, repo_groups: dict,
            config: dict, existing_pulp_servers: dict):
        """Calculates the updates that are needed to pulp server and their repo group config.
        Returns a list of dicts, where the dict has the following key values:
            - pulp_server: pulp server object in the DB to update
            - pulp_server_config: config for the pulp server to be update
            - repo_groups_to_add: List of dicts containing the repo groups to add
            - repo_groups_to_update: List of dicts containg repo group config to update
            - repo_groups_to_remove: List of PulpServerRepoGroup which should be removed
        :param pulp_servers: list of pulp servers enties from the db that are still in the
                             loaded sync config
        :type pulp_servers: list
        :param repo_groups: dict of repo_groups where the key can accesed via theid or name
                            of the repo group, and the value is the group eneity from the database.
        :type repo_groups: dict
        :param existing_pulp_servers: dict of pulp servers that exist in the db. Key is name of
                                      pulp server value is pulp server entity
        :return: list
        """

        log.info("calculating pulp servers that need updates")
        pulp_servers_to_update = []
        for pulp_server in pulp_servers:
            updates_needed = False
            pulp_server_update_config = {
                "pulp_server": pulp_server,
                "pulp_server_config": {},
                "repo_groups_to_add": [],
                "repo_groups_to_update": [],
                "repo_groups_to_remove": []
            }

            # For when a pulp server has been removed from config file
            if pulp_server.name not in config["pulp_servers"]:
                continue

            pulp_server_config = config["pulp_servers"][pulp_server.name]
            credentials_config = config["credentials"][pulp_server_config["credentials"]]

            pulp_server_entity_config = self._get_pulp_server_entity_config(
                pulp_server.name, pulp_server_config, credentials_config
            )
            pulp_server_update_config["pulp_server_config"] = {}

            for key, value in pulp_server_entity_config.items():
                if getattr(pulp_server, key) != value:
                    updates_needed = True
                    pulp_server_update_config["pulp_server_config"][key] = value

            pulp_server_update_config["repo_groups_to_add"] = self._calculate_pulp_server_repo_groups_to_add(
                pulp_server, repo_groups, config, existing_pulp_servers
            )

            pulp_server_update_config["repo_groups_to_update"] = self._calculate_pulp_server_repo_groups_to_update(
                pulp_server, repo_groups, config, existing_pulp_servers
            )

            pulp_server_update_config["repo_groups_to_remove"] = self._calculate_pulp_server_repo_groups_to_remove(
                pulp_server, repo_groups, config
            )

            if (len(pulp_server_update_config["repo_groups_to_add"]) > 0 or
                    len(pulp_server_update_config["repo_groups_to_update"]) > 0 or
                    len(pulp_server_update_config["repo_groups_to_remove"]) > 0):
                updates_needed = True

            if updates_needed:
                pulp_servers_to_update.append(pulp_server_update_config)

        log.info(f"{len(pulp_servers_to_update)} need to be updated")
        return pulp_servers_to_update

    def _calculate_pulp_servers_to_remove(self, pulp_servers: List[PulpServer], config: dict):
        """Returns a list of pulp servers that need to be removed from the DB
        :param pulp_servers: List of PulpServer entities that exist in the DB
        :type pulp_servers: list
        :param config: dict of loaded config from the repo sync file
        :type config: dict
        :return: list
        """

        log.info("calculating pulp servers that can be removed from Pulp Manager")
        expected_pulp_servers = config['pulp_servers'].keys()

        #pylint: disable=line-too-long
        pulp_servers_to_remove = [
            pulp_server for pulp_server in pulp_servers if pulp_server.name not in expected_pulp_servers
        ]
        log.info(f"{len(pulp_servers_to_remove)} pulp servers to be removed from Pulp Manager")

        return pulp_servers_to_remove

    def _process_pulp_servers(self, config: dict, repo_groups: dict):
        """Adds/updates/removes any pulp servers and their associated repo groups based on the
        config dict passed through.
        :param config: Loaded config from yaml file which specifies pulp sync config
        :type config: dict
        :param repo_groups: dict of RepoGroup entities that exist in the db. A repo group
                            can be obtained using either the name of the repo group or
                            its id
        :type repo_groups: dict
        """

        pulp_servers_in_db = self._add_pulp_servers(config)
        pulp_servers = []
        #pylint: disable=unused-variable
        for pulp_server_name, pulp_server in pulp_servers_in_db.items():
            pulp_servers.append(pulp_server)

        pulp_servers_to_update = self._calculate_pulp_server_updates(
            pulp_servers, repo_groups, config, pulp_servers_in_db
        )
        pulp_servers_to_remove = self._calculate_pulp_servers_to_remove(pulp_servers, config)

        for pulp_update_config in pulp_servers_to_update:
            self._update_pulp_server(pulp_update_config)

        if len(pulp_servers_to_remove) > 0:
            self._remove_pulp_servers(pulp_servers_to_remove)

    def load_config(self, file_path: str):
        """Loads config, updates the database with pulp servers and their repo groups
        and creates the scheduled jobs in redis
        """

        log.info(f"loading config from {file_path} and updating db")
        config = parse_config_file(file_path)
        repo_groups = self._process_repo_groups(config["repo_groups"])
        self._process_pulp_servers(config, repo_groups)
        log.info("config successfully loaded")

"""Carries out ldap authentication
"""
#pylint:disable=no-member
import os
import re
import socket
import traceback
import ldap
from pulp_manager.app.config import CONFIG
from pulp_manager.app.exceptions import PulpManagerLdapError
from pulp_manager.app.utils import log


# REQUEST_CA_BUNDLE is set in dockerfile so that libraries that use
# requests use the global cert bundle for validating SSL instead
# of the once in the venv. Set ldap library to also use the file
if "REQUESTS_CA_BUNDLE" in os.environ:
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, os.environ["REQUESTS_CA_BUNDLE"])


def get_connection_string(ldap_server: str):
    """Gets the connection string for an ldap server

    :param ldap_server: ldap server to generate the connection for
    :type ldap_server: str
    :return: str
    """

    protocol = "ldaps" if bool(CONFIG["auth"]["use_ssl"]) else "ldap"
    return f"{protocol}://{ldap_server}"


def ldap_server_available(ldap_server: str):
    """Tests the LDAP connection for the given ldap server.
    Raises and exception when the ldap server can't be contacted

    :param ldap_server: ldap server to test the connection of
    :type ldap_server: str
    """

    connection_string = get_connection_string(ldap_server)
    log.info(f"Testing ldap connection to {connection_string}")

    port = 636 if connection_string.split(":")[0] == "ldaps" else 389
    address = connection_string.split('//')[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((address, port))
    if result != 0:
        error = f"Could not connect to ldap on {connection_string}"
        log.error(error)
        raise PulpManagerLdapError(error)


# pylint: disable=too-many-locals
def auth_user(username: str, password: str):
    """Carries out LDAP authentication, returns the list of groups the
    user is a member of. Group are given as name, not the full distinguished
    name of the LDAP User

    :param username: username of user being authenticated
    :type username: str
    :param password: password of user being authenticated
    :type password: str
    :return: list
    """

    log.info(f"Beginning LDAP authentication for username: {username}")
    ldap_server_errors = []
    groups = []

    # Need to ensure that username is of format DOMAIN\Username if it is just
    # username in some instances authentication may fail for some users even
    # if they are using the correct credentials
    if r"\\" not in username:
        log.info(f"Prefixing {CONFIG['auth']['default_domain']} to {username}")
        username = fr"{CONFIG['auth']['default_domain']}\{username}"
        log.info(f"Updated username: {username}")

    for ldap_server in CONFIG["auth"]["ldap_servers"].split(","):
        try:
            connection_string = get_connection_string(ldap_server)
            log.info(f"Initializing LDAP connection to: {connection_string}")
            connection = ldap.initialize(connection_string)
            connection.protocol_version = ldap.VERSION3
            # disable referrals
            connection.set_option(ldap.OPT_REFERRALS, 0)

            log.info(f"Authenticating {username}")
            connection.simple_bind_s(username, password)

            log.info(f"Getting groups user {username} is a member of")
            username_domain_strip = username.replace(f"{CONFIG['auth']['default_domain']}\\", "")
            result = connection.search_s(
                CONFIG["auth"]["base_dn"],
                ldap.SCOPE_SUBTREE,
                f"samAccountName={username_domain_strip}",
                ["memberOf"]
            )

            for group in result[0][1]['memberOf']:
                group_decode = group.decode()
                match = re.match(r'CN=([A-z0-9\-]+),[OU|DC|ou|dc]', group_decode)
                groups.append(match.group(1))

            log.info("group memebership retrieved")
        except ldap.LDAPError as exception:
            error_dict = exception.args[0]
            result = error_dict["result"]
            desc = error_dict["desc"] if "desc" in error_dict else None
            info = error_dict["info"] if "info" in error_dict else None

            log.error(
                f"Error authenticating user {username} against {ldap_server}, "
                f"result: {result}, desc: {desc}, info: {info}"
            )
            log.error(traceback.format_exc())

            if isinstance(exception, ldap.NO_SUCH_OBJECT):
                raise

            ldap_server_errors.append(f"Error: result: {result}, desc: {desc}")
            continue

    if len(ldap_server_errors) > 0:
        error = f"LDAP errors authenticating: {username}. {','.join(ldap_server_errors)}"
        raise PulpManagerLdapError(error)

    return groups

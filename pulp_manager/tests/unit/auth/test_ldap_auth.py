"""Carries out the LDAP auth tests
"""
import pytest
import configparser
import ldap
from mock import patch

from pulp_manager.app.auth.ldap_auth import get_connection_string, ldap_server_available, auth_user
from pulp_manager.app.exceptions import PulpManagerLdapError


class TestLdapAuth:
    """Class for testing ldap auth
    """

    def test_get_connection_string(self):
        """Tests the correct connection string is returned for an ldap server
        """

        result = get_connection_string("dc.domain.local")
        assert result == "ldaps://dc.domain.local"

    @patch("pulp_manager.app.auth.ldap_auth.socket.socket.connect_ex")
    def test_ldap_server_available_ok(self, mock_connect_ex):
        """Tests that when the port on an ldap server can be successfully connected to
        no error is thrown
        """

        mock_connect_ex.return_value = 0
        ldap_server_available("dc.domain.local")

    @patch("pulp_manager.app.auth.ldap_auth.socket.socket.connect_ex")
    def test_ldap_server_available_fail(self, mock_connect_ex):
        """Tests that when the port on an ldap server cannot be connected to
        an error is thrown
        """

        mock_connect_ex.return_value = 1

        with pytest.raises(PulpManagerLdapError):
            ldap_server_available("dc.domain.local")

    @patch("ldap.ldapobject.SimpleLDAPObject.search_s")
    @patch("ldap.ldapobject.SimpleLDAPObject.simple_bind_s")
    @patch("pulp_manager.app.auth.ldap_auth.ldap.initialize")
    def test_auth_user_ok(self, mock_ldap_initialize, mock_ldap_bind, mock_ldap_search):
        """Tests that a list of groups is returned when a user is successfully authenticated
        """

        mock_ldap_initialize.return_value = ldap.ldapobject.SimpleLDAPObject('ldap://fakeuri')
        # Mock search returns a list of tuples which contain matching users
        mock_ldap_search.return_value = [
            (
                "CN=fake-user,DC=fake,DC=local",
                {
                    "memberOf": [
                        b"CN=group1,OU=ou,DC=fake,DC=local",
                        b"CN=group2,OU=ou2,OU=ou,DC=fake,DC=local",
                        b"CN=group3,DC=fake,DC=local"
                    ]
                }
            )
        ]

        expected = ["group1", "group2", "group3"]
        seen = auth_user("fake_user", "fake_pass")

        assert seen == expected

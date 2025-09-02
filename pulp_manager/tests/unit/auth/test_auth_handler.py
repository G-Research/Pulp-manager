"""Tests for JWT signing and decoding
"""

from mock import patch
from pulp_manager.app.auth.auth_handler import sign_jwt, decode_jwt, authenticate


class TestAuthHandler:
    """Tests JWT signing and decoding
    """

    def test_sign_decode_jwt(self):
        """Tests that generating a JWT can then be decoded
        """

        username = "fake_user"
        groups = ["group1", "group2", "group3"]
        access_token = sign_jwt(username, groups)

        assert "access_token" in access_token

        decoded_jwt = decode_jwt(access_token["access_token"])

        assert decoded_jwt["username"] == username
        assert decoded_jwt["groups"] == groups


    @patch("pulp_manager.app.auth.ldap_auth.auth_user")
    def test_authenticate(self, mock_auth_user):
        """Tests that authenticate returns a signed JWT with groups and username
        """

        username = "fake_user"
        groups = ["group1", "group2", "group3"]

        mock_auth_user.return_value = groups

        access_token = authenticate(username, groups)
        decoded_jwt = decode_jwt(access_token["access_token"])
        assert decoded_jwt["username"] == username
        assert decoded_jwt["groups"] == groups

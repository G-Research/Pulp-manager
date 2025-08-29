"""Carries out tests for v1 pulp_servers routes
"""
import fakeredis
from mock import patch
from fastapi.testclient import TestClient

from pulp_manager.app.auth.auth_handler import sign_jwt, decode_jwt


class TestAuthV1Routes:
    """Testing of auth routes
    """

    @patch("pulp_manager.app.auth.ldap_auth.auth_user")
    def test_login(self, mock_auth_user, client: TestClient):
        """Tests that login returns a signed jwt
        """

        username = "fake_user"
        groups = ["group1", "group2", "group3"]

        mock_auth_user.return_value = groups

        result = client.post(
            client.app.url_path_for("auth:login"),
            json={"username": "fake_user", "password": "password"}
        )
        assert result.status_code == 200
        assert "access_token" in result.json()

        decoded_jwt = decode_jwt(result.json()["access_token"])
        assert decoded_jwt["username"] == username
        assert decoded_jwt["groups"] == groups

    def test_token_lookup(self, client: TestClient):
        """Tests that the token lookup returns information about a valid token
        """

        username = "fake_user"
        groups = ["group1", "group2", "group3"]

        signed_jwt = sign_jwt(username, groups)
        token_lookup_url = f"{client.app.url_path_for('auth:token_lookup')}?token={signed_jwt['access_token']}"
        result = client.get(token_lookup_url)
        assert result.status_code == 200
        assert result.json()["username"] == username
        assert result.json()["groups"] == groups

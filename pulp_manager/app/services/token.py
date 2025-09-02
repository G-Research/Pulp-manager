"""Service for decoding JWTs
"""

from typing import Dict
from pulp_manager.app.auth import decode_jwt
from pulp_manager.app.exceptions import PulpManagerTokenError
from pulp_manager.app.services.base import PulpManagerService


class TokenService(PulpManagerService):
    """User token lookup service.
    """

    def decode_jwt(self, token: str) -> Dict[str, str]:
        """Takes a JWT token and returns the decoded token. If empty token
        is returned then an exception is raised

        :param token: JWT token to decode
        :type token: str
        :return: dict
        """

        decoded_jwt = decode_jwt(token)
        if len(decoded_jwt) == 0:
            raise PulpManagerTokenError("Failed to decode JWT. It has probably expired")
        return decoded_jwt

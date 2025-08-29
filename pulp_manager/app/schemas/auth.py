"""API Schemas models relating to auth
"""

# pylint: disable=no-name-in-module
from pydantic import BaseModel


class UsernamePasswordLogin(BaseModel):
    """Username and password details for authentication
    """

    username: str
    password: str


class JWTSignedToken(BaseModel):
    """Result of a successful login which gives a signed JWT token
    """

    access_token: str


class JWTDecodedToken(BaseModel):
    """Content that is stored in a decoded JWT token
    """

    username: str
    groups: list
    expires: str

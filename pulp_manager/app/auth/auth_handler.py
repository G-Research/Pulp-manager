"""Entry point into all authentication servers
"""

# pylint: disable=broad-except
import time
from datetime import datetime, timezone
import os
import re
from typing import Dict
import traceback
from fastapi import Request
import jwt

from pulp_manager.app.config import CONFIG
from pulp_manager.app.exceptions import PulpManagerPulpConfigError
from pulp_manager.app.utils import log


JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = CONFIG["auth"]["jwt_algorithm"]
JWT_LIFETIME = int(CONFIG["auth"]["jwt_token_lifetime_mins"])


def get_jwt(request: Request) -> str:
    """Gets the jwt from the request headers

    :param request: Request object that contains headers and other parameters passed
    :type request: Request
    :return: str
    """

    log.info("Retrieving JWT from request")
    token = request.headers["authorization"]
    return re.match('Bearer (.*)', token).groups(1)[0]


def sign_jwt(username: str, groups: list) -> Dict[str, str]:
    """Signs the JWT and returns the access token

    :param username: username of user that was authenticated
    :type username: str
    :param groups: list of groups user is a member of
    :type groups: list
    :return: dict
    """

    log.info("Signing JWT for {username}")
    payload = {
        "username": username,
        "groups": groups,
        "expires": time.time() + (JWT_LIFETIME * 60) # convert lifetime to seconds
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"access_token": token}


def decode_jwt(token: str) -> dict:
    """Decodes the JWT and returns a dict with the decoded data.
    An empty dict is returned in the token has expired

    :param token: JWT token to decode
    :type token: str
    :return: dict containing the JWT decoded data
    """

    try:
        log.info("Attempting to decode JWT")
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_expiry = decoded_token["expires"]
        expiry_time_utc = datetime.fromtimestamp(token_expiry, timezone.utc)
        decoded_token["expires"] = expiry_time_utc.strftime("%H:%M:%S %d-%m-%Y UTC")
        return decoded_token if token_expiry >= time.time() else None
    except Exception:
        log.exception("Failed to decode JWT")
        log.error(traceback.format_exc())
        return {}


def authenticate(username: str, password: str) -> Dict[str, str]:
    """Authenticates a user and returns a signed JWT containing the list og groups
    that the usern is a member of

    :param username: username of user being authenticated
    :type username: str
    :param password: password of user being authenticated
    :type password: str
    :return: str
    """

    supported_authentication = ["ldap"]

    # pylint: disable=import-outside-toplevel
    if CONFIG["auth"]["method"] == "ldap":
        log.info("Attempting to authenticate {username} with LDAP")
        from .ldap_auth import auth_user
    else:
        raise PulpManagerPulpConfigError(
            f"Unsupported authentication type got {CONFIG['auth']['method']}, "
            f"allowed {', '.join(supported_authentication)}"
        )

    groups = auth_user(username, password)
    return sign_jwt(username, groups)

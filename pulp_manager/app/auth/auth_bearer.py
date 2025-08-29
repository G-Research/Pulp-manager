"""Custom JWT Auth Bearer. Taken from: https://testdriven.io/blog/fastapi-jwt-auth/
"""
# pylint: disable=broad-except
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pulp_manager.app.utils import log
from pulp_manager.app.auth.auth_handler import decode_jwt


class JWTBearer(HTTPBearer):
    """Custom HTTP bearer for JWT support
    """

    def __init__(self, auto_error: bool = True, allowed_groups = None):
        """Constructor setup

        :param allowed_groups: Adding for UADB JWTBearer, this is a list of groups that are allowed
                               to call the endpoint to make changes to the database
        :type allowed_groups: list
        """

        self.allowed_groups = allowed_groups
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        """Check the correct credentials scheme is passed, and validate user is member
        of the correct groups, if allowed_groups is not None
        """

        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        # pylint: disable=no-else-return
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme, only Bearer is allowed"
                )

            log.info("Attempting to decode JWT")
            jwt_payload = self.verify_jwt(credentials.credentials)
            log.info(f"Checking user {jwt_payload['username']} is allowed to access endpoint")

            if jwt_payload is None:
                raise HTTPException(status_code=403, detail="Invalid token of expired token")

            if self.allowed_groups is not None:
                user_in_group = False
                for group in self.allowed_groups:
                    if group in jwt_payload['groups']:
                        user_in_group = True
                        break

                if not user_in_group:
                    log.info(
                        f"User {jwt_payload['username']} not in groups "
                        f"{', '.join(self.allowed_groups)}, to carry out: "
                        f"{request.method} - {request.url}"
                    )

                    raise HTTPException(
                        status_code=401,
                        detail=(
                            "Unauthroized, only users in the groups "
                            f"{', '.join(self.allowed_groups)} are allowed to cary out"
                            f"{request.method} - {request.url}"
                        )
                    )
                log.info(
                    f"User {jwt_payload['username']} is allowed to access endpoint {request.url}"
                )
                return credentials.credentials
            else:
                raise HTTPException(status_code=403, detail="Invalid authorization code")

    def verify_jwt(self, token: str) -> bool:
        """Checks if the JWT is valid, reutrn bool

        :param token: JWT to vlaidate
        :type token: str
        :return: bool
        """

        try:
            payload = decode_jwt(token)
        except Exception:
            payload = None

        return payload

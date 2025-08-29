"""router for tasks route
"""
# pylint: disable=too-many-arguments,unused-argument,redefined-builtin,too-many-locals
from fastapi import APIRouter

from pulp_manager.app.auth import authenticate
from pulp_manager.app.route import LoggingRoute
from pulp_manager.app.schemas import UsernamePasswordLogin, JWTSignedToken, JWTDecodedToken
from pulp_manager.app.services import TokenService


auth_v1_router = APIRouter(
    prefix='/v1/auth',
    tags=['auth'],
    responses={404: {'description': 'Not Found'}},
    route_class=LoggingRoute
)


@auth_v1_router.post('/login', name="auth:login", response_model=JWTSignedToken)
def login(user_login: UsernamePasswordLogin):
    """Uses username and password authentication for LDAP logins
    """

    return authenticate(user_login.username, user_login.password)


@auth_v1_router.get('/token_lookup', name='auth:token_lookup', response_model=JWTDecodedToken)
def token_lookup(token: str):
    """Returns decoded JWT token
    """

    return TokenService().decode_jwt(token)

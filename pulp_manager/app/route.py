"""Custom route to provide consistant route logging for all requests
"""
# pylint: disable=broad-except,raise-missing-from
import json
import re
import traceback
from typing import Callable
#import ldap

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute

from pulp_manager.app.middleware import get_request_id
from pulp_manager.app.auth import decode_jwt
from pulp_manager.app.utils import log


def parse_route_args(**kwargs):
    """Parses routing args for use by services,
    and drops any arguments that are not needed/would cause
    problems. E.g db which is db connection to backend database
    :param kwargs: kwargs to process
    :type kwargs: dict
    :returns: dict
    """

    query_params = {}
    for key, value in kwargs.items():
        if key not in ['request', 'db', 'pdb'] and value is not None:
            query_params[key] = value
    return query_params


# pylint: disable:logging-format-interpolation,fixme,raise-missing-from
class LoggingRoute(APIRoute):
    """Custom route to handle logging of exceptions from
    all routes in a consistant way
    """

    def get_route_handler(self) -> Callable:
        """Carries out the handling of the route
        """

        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            """Custom logic to apply to all routes
            :param request: Request object containing route information
            :type request: starlette.requests.Request
            """

            # Get body as bytes first, will be None if erquest had no body
            request_id = get_request_id()
            body = await request.body()

            if body:
                body = body.decode()

            # body will be a string, see if we can convert to dict and strip password if contained
            body_clone = body
            try:
                body_dict = json.loads(body_clone)
                if 'password' in body_dict.keys():
                    body_dict['password'] = '******'
                    body_clone = json.dumps(body_dict)
            except Exception:
                log.info('Body not json serializable')
                if '/login/' in str(request.url):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Body not json serializable, request_id: {request_id}"
                    )


            # Strip out token from query params logging
            query_params_clone = dict(request.query_params)
            if 'token' in query_params_clone.keys():
                query_params_clone['token'] = '******'

            # Strip out token from URL so it isn't logged
            request_url_clone = re.sub(
                r"token=([A-z0-9\._-]+)\&*\/*", 'token=*****', str(request.url)
            )

			# this will be corrected in future when there is aut again
            user_info = ''
            if 'authorization' in request.headers.keys():
                authorization_header = request.headers['authorization']
                match = re.match("Bearer (.*)", authorization_header)
                auth_payload = decode_jwt(match.group(1))
                user_info = f"username: {auth_payload['username']}"

            client = request.client.host
            if 'X-Real-IP' in request.headers:
                client = request.headers['X-Real-IP']

            log.info(
               (f"client: {client}, method: {request.method}, url: {request_url_clone}, "
                f"query_parameters: {query_params_clone}, path_parameters: {request.path_params}, "
                f"body: {body_clone}, {user_info}")
            )

            try:
                return await original_route_handler(request)
            except HTTPException as exception:
                log.error(exception)
                log.error(traceback.format_exc())
                raise HTTPException(
                    status_code=exception.status_code,
                    detail=f"{exception.detail}, request_id: {request_id}"
                )
            except Exception as exception:
                log.error(f"Unexpected error ocurred. {type(exception)} - {str(exception)}")
                log.error(traceback.format_exc())
                raise HTTPException(
                    status_code=500,
                    detail=(f"An unexpected error occured: {str(exception)} "
                        f"request_id: {request_id}")
                )

        return custom_route_handler

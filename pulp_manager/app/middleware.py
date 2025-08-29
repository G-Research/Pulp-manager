"""Sets up a custom middleware for adding a request_id, to a request so
that it can be tracked through classes
taken from: https://github.com/encode/starlette/issues/420
"""
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request


REQUEST_ID_CTX_KEY = "request_id"

_request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default=None)


def get_request_id() -> str:
    """Gets the request ID that has been generated for tracing the request
    """

    return _request_id_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request_id to a request
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Dispatches request and retruns the response
        """
        request_id = _request_id_ctx_var.set(str(uuid4()))
        response = await call_next(request)
        _request_id_ctx_var.reset(request_id)
        return response

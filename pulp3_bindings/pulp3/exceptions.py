"""Custom exceptions for pulp3"""


class PulpV3Error(Exception):
    """Generic pulp v3 exception task
    """


class PulpV3APIError(PulpV3Error):
    """Exception to throw when error is returned from API
    """


class PulpV3InvalidArgumentError(PulpV3Error):
    """Exception to throw when wrong argument is specified
    """


class PulpV3InvalidTypeError(PulpV3Error):
    """Exception to throw when wrong type specified for href
    """


class PulpV3TaskStuckWaiting(PulpV3Error):
    """Raised when a task fails to enter the running state
    """


class PulpV3TaskFailed(PulpV3Error):
    """Raised when a Pulp task has failed
    """

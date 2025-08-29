"""Custom exceptions for PulpManager
"""

class PulpManagerError(Exception):
    """Base exception all pulp manager exceptions inherit from
    """


class PulpManagerValueError(PulpManagerError):
    """Raised when invalid value is passed to Pulp Manager
    """


class PulpManagerInvalidPageSize(PulpManagerError):
    """Raised when too large a page size is required for paged results
    """


class PulpManagerPulpTaskError(PulpManagerError):
    """Raised when a task on a pulp server fails
    """


class PulpManagerEntityNotFoundError(PulpManagerError):
    """Raised when entity can't be found in the DB
    """


class PulpManagerTaskNotFoundError(PulpManagerEntityNotFoundError):
    """Specific entity type error when a task can't  be found in the DB
    """


class PulpManagerFilterError(PulpManagerError):
    """Error rasied on when there are problems parsing the filter options that have been passed
    to a repository for querying entities
    """


class PulpManagerPulpConfigError(PulpManagerError):
    """exception raised when pulp manager config is invalid
    """


class PulpManagerSnapshotError(PulpManagerError):
    """Raised when an issue with snapshot configuration
    """


class PulpManagerTaskInvalidStateError(PulpManagerError):
    """Raised when trying to move a task into an invalid state
    """


class PulpManagerLdapError(PulpManagerError):
    """Raised when there is an issue with ldap auth
    """


class PulpManagerTokenError(PulpManagerError):
    """Raised when there is an issue with the users JWT
    """

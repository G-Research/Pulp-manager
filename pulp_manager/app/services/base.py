"""Base classes all services inherit from
"""
from sqlalchemy.orm import Session

class PulpManagerService:
    """Base service all PulpManager services inheirt from
    """


class PulpManagerDBService(PulpManagerService):
    """PulpManager services that use the DB inheirt from this service
    """

    def __init__(self, db: Session):
        """Constructor
        :param db: DB session to use
        :type db: Session
        """

        self.db = db


class PulpServerService(PulpManagerService):
    """Services that carry out actions on a pulp server
    """

    def __init__(self, db: Session, name: str):
        """Constructor
        :param db: DB session to use
        :type db: Session
        :param name: name of the pulp instance to carry out interaction on
        :type name: str
        """

        self._db = db
        self._name = name

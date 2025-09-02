"""Bases models for pulp_manager
"""

from datetime import datetime
import sqlalchemy
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase


class PulpManagerBase(DeclarativeBase):
    """Base model all pulp manager models inheirt from
    """
    __abstract__ = True

    #pylint: disable=not-callable
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    date_last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=datetime.utcnow()
    )

    def _repr(self, **fields):
        """Dict of fields taken to build the string representation
        of the instance.
        """

        field_strings = []
        at_least_one_attached_attribute = False
        for key, field in fields.items():
            try:
                field_strings.append(f'{key}={field!r}')
            except sqlalchemy.orm.exc.DetachedInstanceError:
                # In we have ended up with a DetachedInstanceError then we have
                # probably done something funny with the session
                field_strings.append(f'{key}=DetachedInstanceError')
            else:
                at_least_one_attached_attribute = True
        if at_least_one_attached_attribute:
            return f"<{self.__class__.__name__}({','.join(field_strings)})>"
        return f"<{self.__class__.__name__} {id(self)}>"


class PulpManagerBaseId(PulpManagerBase):
    """Base model for all models that have an ID field as their primary key
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    def __repr__(self):
        """Override the SQLAlchemy representation of the model
        Calls a build in helper, for a more flexible way to generate
        the string
        """

        return self._repr(id=self.id)

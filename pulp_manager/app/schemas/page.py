"""Base page config
"""

from typing import Generic, TypeVar, List
from pydantic.generics import GenericModel


DataT = TypeVar('DataT')


class Page(GenericModel, Generic[DataT]):
    """Schema model for returning paged items
    """

    items: List[DataT]
    total: int
    page: int
    page_size: int

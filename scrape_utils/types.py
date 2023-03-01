"""types.py.

General types for scrape-utils.
"""
from typing import TypeVar

from .models.base import Base
from .models.redis import ScrapeItemBase

# ModelType = TypeVar("ModelType", bound="Base")
ModelType = TypeVar("ModelType", bound=Base)
# ModelType = TypeVar("ModelType", bound=Base, covariant=True)
CreateType = TypeVar("CreateType", bound=Base)
PatchType = TypeVar("PatchType", bound=Base)

ScrapeItemType = TypeVar("ScrapeItemType", bound=ScrapeItemBase)

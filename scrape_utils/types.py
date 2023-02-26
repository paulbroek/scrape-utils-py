"""types.py.

General types for scrape-utils.
"""
from typing import TypeVar

from .models.base import Base

# ModelType = TypeVar("ModelType", bound="Base")
ModelType = TypeVar("ModelType", bound=Base, covariant=True)
CreateType = TypeVar("CreateType", bound=Base)
PatchType = TypeVar("PatchType", bound=Base)

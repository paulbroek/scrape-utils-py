"""typer.py.

Utility helper functions for working with Typer CLI apps
"""

import importlib

import typer
from scrape_utils.models.redis import CollectionBase


def collection_validator(library_name: str, collection_member: str) -> CollectionBase:
    """Import collection dynamically from custom package."""
    try:
        redis_module = importlib.import_module(f"{library_name}.models.redis")
    except ModuleNotFoundError:
        raise typer.BadParameter(
            f"{library_name} has no `models.redis.Collection` class"
        )

    collection_class = redis_module.Collection

    try:
        collection = getattr(collection_class, collection_member)
    except AttributeError:
        raise typer.BadParameter(
            f"{collection_class=} has no attribute `{collection_member}`. available members: {list(collection_class.__members__)}"
        )

    return collection

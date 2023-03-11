import logging
from datetime import datetime
from typing import Final, Sequence, Set

from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

DATETIME_FIELDS_BASE: Final[Set[str]] = set(
    [
        "last_scraped",
        "created_at",
        "updated_at",
    ]
)


class Base(SQLModel):
    """Base model.

    Only implements helper functions for base scrape model
    """

    @classmethod
    def _date_parser(
        cls, json_data: dict, dt_fields_extra: Sequence[str] = tuple(), **kwargs
    ) -> dict:
        """Parse dates from isoformat to datetime."""
        # if present, cast isoformat dates to datetime
        json_data |= kwargs

        dt_fields: Set[str] = DATETIME_FIELDS_BASE | set(dt_fields_extra)

        for key in dt_fields:
            if key in json_data and isinstance(json_data[key], str):
                json_data[key] = datetime.fromisoformat(json_data[key])

        return json_data

    @classmethod
    def from_json(cls, json_data: dict, **kwargs):
        """Create instance from json dict."""
        json_data_new: dict = cls._date_parser(json_data, **kwargs)

        return cls(**json_data_new)

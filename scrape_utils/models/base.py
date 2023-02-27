import logging
from datetime import datetime

from sqlmodel import SQLModel

logger = logging.getLogger(__name__)


class Base(SQLModel):
    """Base model.

    Only implements helper functions
    """

    @classmethod
    def _date_parser(cls, json_data: dict, **kwargs) -> dict:
        """Parse dates from isoformat to datetime."""
        # if present, cast isoformat dates to datetime
        # all_data = json_data | kwargs
        json_data |= kwargs

        for key in (
            "time_start",
            "time_end",
            "last_scraped",
            "created_at",
        ):
            if key in json_data and isinstance(json_data[key], str):
                json_data[key] = datetime.fromisoformat(json_data[key])

        return json_data

    @classmethod
    def from_json(cls, json_data: dict, **kwargs):
        """Create instance from json dict."""
        json_data_new: dict = cls._date_parser(json_data, **kwargs)

        return cls(**json_data_new)

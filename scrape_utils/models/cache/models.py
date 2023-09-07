import sys
from datetime import datetime
from typing import Final, Optional, Self

import lz4.block as lz4  # type: ignore[import]
from pydantic import BaseModel
from scrape_utils.models.main import UUIDModel
from scrapy.http import Headers
from sqlalchemy.orm import registry
from sqlmodel import Field

# from ..scrape import ScrapeBaseMixin
from ..scrape import ScrapeBase

mapper_registry = registry()


def kb_size(item) -> int:
    return int(sys.getsizeof(item) / 1024)


# class HttpCacheItemBase(BaseModel):
# class HttpCacheItemBase(ScrapeBaseMixin):
class HttpCacheItemBase(ScrapeBase):
    status: int = Field(nullable=False)
    url: str = Field(nullable=False, unique=True, index=True)
    # headers: Headers
    headers: Optional[bytes] = Field(nullable=True)
    # compressed bytes
    body: bytes = Field(nullable=False)
    time: float = Field(nullable=False)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"status={self.status}, "
            f"url='{self.url}', "
            f"id='{self.uuid}', "
            f"headers={self.headers}, "
            f"body='...' ({kb_size(self.body):,}), "
            f"time={self.time}"
            f")"
        )


# @mapper_registry.mapped
class HttpCacheItem(HttpCacheItemBase, UUIDModel, table=True):
    __tablename__ = f"http_cache_items"

    @classmethod
    # requires py 3.11
    # def from_response(cls, response):
    def from_response(cls, response) -> Self:
        time: Final[float] = datetime.utcnow().timestamp()
        # time = datetime.utcnow().timestamp()

        data = {
            "status": response.status,
            "url": response.url,
            "headers": response.headers.to_string,
            # "body": _compress(response.body),
            "body": lz4.compress(response.body),
            "time": time,
            "last_scraped": datetime.utcnow(),
        }

        return cls(**data)

    __mapper_args__ = {
        "polymorphic_identity": "http_cache_items",
        # "concrete": True,
    }


class HttpCacheItemRead(HttpCacheItemBase):
    pass


class HttpCacheItemPatch(HttpCacheItemBase):
    pass

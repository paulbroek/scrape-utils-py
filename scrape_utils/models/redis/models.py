from datetime import datetime
# from enum import StrEnum
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DataSourceUrls(str, Enum):
    redis = "redis"
    jl_file = "jl_file"
    sitemap = "sitemap"
    pg_http_cache = "pg_http_cache"


class DataSourceScrapeItems(str, Enum):
    redis = "redis"
    jl_file = "jl_file"


class UrlRecord(BaseModel):
    url: str


class SitemapRecord(UrlRecord):
    lastmod: datetime


# want to use StrEnum, but py 3.10 needed for sqlalchemy
class CollectionBase(str, Enum):
    pass


class ScrapeItem(BaseModel):
    # question: want to type enforce during scrape process
    # or dump raw to redis, and parse later?
    # item: ScrapeBase
    item: dict
    crawled: datetime
    spider: str
    type: CollectionBase
    version: Optional[str]

    class Config:
        json_encoders = {
            # custom output conversion for your type
            datetime: lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")
        }

"""helpers.py.

helper methods for working with redis models
"""

import gzip
import io
import logging
import os
import urllib
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, TypeVar

import pandas as pd
import requests  # type: ignore[import]
from fastapi import status
from rarc_utils.misc import validate_url
from redis import asyncio as aioredis
from scrape_utils.core.db import get_session  # type: ignore[import]
from scrape_utils.core.redis_connection import redis_connection
from sqlmodel import select
from yapic import json  # type: ignore[import]

from ...cache_http.helpers import get_start_urls_from_pg_cache
from ...core.settings import REDIS_SITEMAP_KEY_FORMAT, START_URLS_KEY
from .models import (CollectionBase, DataSourceScrapeItems, DataSourceUrls,
                     SitemapRecord, UrlRecord)

logger = logging.getLogger(__name__)

DataFrameOrNone = Optional[pd.DataFrame]

INVALID_URL: Final[str] = "Invalid URL"
MAX_CONNECTIONS: Final[int] = 100

ModelType = TypeVar("ModelType")
ScrapeItem = TypeVar("ScrapeItem")


# TODO: how to structure this file and helpers in general. Or use a class?


def parse_unzip_url(url: str) -> DataFrameOrNone:
    """Request xml url and parse the contents."""
    if not validate_url(url):
        raise ValueError(INVALID_URL)
    response = requests.get(url, timeout=10)
    if response.status_code == status.HTTP_200_OK:
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
            df = pd.read_xml(gz)
        return df

    return None


def read_sitemap_base(url: str) -> DataFrameOrNone:
    """Read sitemap from xml file, parse to DataFrame."""
    if not validate_url(url):
        raise ValueError(INVALID_URL)

    logger.info(f"{url=}")
    try:
        df: pd.DataFrame | pd.Series = pd.read_xml(url)

        if isinstance(df, pd.Series):
            raise Exception("should be dataframe")
        return df

    except urllib.error.HTTPError as e:
        if e.status == status.HTTP_403_FORBIDDEN:
            logging.error(
                f"HTTP 403 error occurred while trying to access the sitemap URL. {url} does not exist"
            )

    else:
        raise Exception

    return None


def sitemap_record_from_row(row: pd.Series) -> SitemapRecord:
    """Create sitemapRecord from dataframe row."""
    assert (
        row.dtype == object
    ), f"All elements of pd.series should be strings, but got {row.dtype}"
    # return SitemapRecord(**row.to_dict())
    str_row: Dict[str, Any] = {str(k): v for k, v in row.to_dict().items()}
    return SitemapRecord(**str_row)


def parse_dict_to_model(
    item: dict, model_class: ModelType, from_json: str = "from_json"
) -> Optional[ModelType]:
    """Implement generic parse method for any model_class."""
    assert hasattr(model_class, from_json)
    from_json_method: Callable = getattr(model_class, from_json)
    assert callable(from_json_method)

    try:
        # return from_json_method(item["item"], last_scraped=item["crawled"])
        return from_json_method(item["item"])

    except Exception as e:
        logger.warning(f"could not parse item={item['item']}, \n\n{e=!r}")
        raise

    return None


def filter_existing_start_urls(
    start_urls: List[SitemapRecord], db_connection_str: str, instance=None
) -> List[SitemapRecord]:
    """Filter out existing start urls, that exist in pg."""
    assert instance is not None
    # get all urls from pg

    q = select(instance.url)
    session = get_session(db_connection_str, echo=False)
    res = list(session.execute(q).scalars().fetchall())

    logger.info(f"{res[:5]=}")

    logger.info(f"start_urls before filtering: {len(start_urls):,}")
    start_urls_in = set([s["url"] for s in start_urls])
    start_urls_exist = set(res)

    start_urls_missing = start_urls_in - start_urls_exist
    # super slow code
    # start_urls = [s for s in start_urls if s['url'] not in ]
    logger.info(f"start_urls after filtering: {len(start_urls_missing):,}")

    return [{"url": i} for i in start_urls_missing]


# SCRAPE_URLS_FILE
# EVENTS_SITEMAP_XML_FILE
async def get_scrape_urls_from_source(
    redis_pool,
    data_source: DataSourceUrls,
    db_connection_str: str,
    random,
    maxn,
    collection,
    scrape_urls_file=None,
    events_sitemap_xml_file=None,
    reverse=False,
) -> List[SitemapRecord]:
    """Get scrape urls from source."""
    assert scrape_urls_file is not None
    assert events_sitemap_xml_file is not None
    scrape_urls: List[SitemapRecord] = []

    match data_source:
        case DataSourceUrls.sitemap:
            if not os.path.exists(events_sitemap_xml_file):
                raise FileNotFoundError(f"{events_sitemap_xml_file=} not found.")

            df = pd.read_xml(events_sitemap_xml_file).rename(columns={"loc": "url"})
            logger.info(f"file contains {df.shape[0]:,} rows")
            RANDOM_OR_HEAD: str = ""

            if random:
                df = df.sample(maxn)
                RANDOM_OR_HEAD = "random"
            elif maxn is not None:
                df = df.head(maxn)
                RANDOM_OR_HEAD = "top"

            logger.info(
                f"read {df.shape[0]:,} {RANDOM_OR_HEAD} rows from {events_sitemap_xml_file}"
            )
            df = df.drop(columns=["lastmod"])
            scrape_urls = df.to_dict(orient="records")

        # load scrape_urls from .jl file
        case DataSourceUrls.jl_file:
            if not os.path.exists(scrape_urls_file):
                raise FileNotFoundError(f"{scrape_urls_file=} not found.")

            with open(scrape_urls_file, "r", encoding="utf-8") as f:
                scrape_urls = [json.loads(line) for line in f]

        # load sitemap from redis list
        case DataSourceUrls.redis:
            async with redis_connection(redis_pool) as client:
                # TODO: use pipeline to have real async benefits

                records: List[SitemapRecord] = await get_sitemap_items(
                    client, collection, maxn, reverse=reverse
                )

                logger.info(f"{records[:2]=}")

                # df = pd.DataFrame([r.dict() for r in records])

                # if df.empty:
                if len(records) == 0:
                    logger.warning("got empty data, first run sitemap_to_redis?")
                    return scrape_urls

                # df = df.drop(columns=["lastmod"])

                # scrape_urls = df.to_dict(orient="records")
                scrape_urls = [r.dict() for r in records]

        case DataSourceUrls.pg_http_cache:
            # get url from existing http_cache
            session = get_session(db_connection_str, echo=False)
            scrape_urls = get_start_urls_from_pg_cache(session, limit=maxn)
            # logger.info(f"{scrape_urls=}")

        case other:
            raise NotImplementedError(f"{other=}")

    return scrape_urls


async def get_sitemap_items(
    client: aioredis.Redis,
    collection: CollectionBase,
    n: Optional[int],
    reverse: bool = False,
) -> List[SitemapRecord]:
    """Get sitemap items from redis."""
    sitemap_redis_key: Final[str] = REDIS_SITEMAP_KEY_FORMAT.format(
        collection=collection.name
    )

    assert await client.exists(
        sitemap_redis_key
    ), f"{sitemap_redis_key=} does not exist"

    logger.info(f"fetching sitemap items from key `{sitemap_redis_key}`")

    items: List[Tuple[Any, float]] = []
    # return oldest items
    if reverse:
        items = await client.zrange(
            sitemap_redis_key, 0, -1 if n is None else n, withscores=True
        )

    else:
        items = await client.zrevrange(
            sitemap_redis_key, 0, -1 if n is None else n, withscores=True
        )

    records: List[SitemapRecord] = [
        SitemapRecord(
            url=url,
            lastmod=datetime.fromtimestamp(int(lastmod)),
        )
        for url, lastmod in items
    ]

    return records


async def delete_sitemap_key(
    client: aioredis.Redis, collection: CollectionBase
) -> None:
    """Delete sitemap key."""
    sitemap_redis_key: Final[str] = REDIS_SITEMAP_KEY_FORMAT.format(
        collection=collection.name
    )
    await client.delete(sitemap_redis_key)
    logger.warning(f"deleted `{sitemap_redis_key}` key in redis")


async def push_sitemap_record_to_redis(
    client: aioredis.Redis, collection: CollectionBase, item: SitemapRecord
) -> None:
    """Push sitemapRecord to redis zset."""
    sitemap_redis_key: Final[str] = REDIS_SITEMAP_KEY_FORMAT.format(
        collection=collection.name
    )
    assert isinstance(item, SitemapRecord)
    await client.zadd(sitemap_redis_key, {item.url: item.lastmod.timestamp()})


async def push_redis_to_scrape(client: aioredis.Redis, item: UrlRecord | dict) -> None:
    """Push to_scrape items to redis list."""
    if isinstance(item, UrlRecord):
        item = item.dict()

    await client.rpush(START_URLS_KEY, json.dumps(item))


async def priority_push_redis_to_scrape(
    client: aioredis.Redis, item: UrlRecord | dict
) -> None:
    """Push to left side of to_scrape items. Will be scraped first."""
    if isinstance(item, UrlRecord):
        item = item.dict()

    await client.lpush(START_URLS_KEY, json.dumps(item))


############################
#### scrape_item methods
############################


async def rem_none_items(client: aioredis.Redis, items_key: str) -> None:
    await client.lrem(items_key, 0, "null")


async def get_redis_scrape_items(
    client: aioredis.Redis, items_key: str, n: int
) -> List[ScrapeItem]:
    """Get scrape_items from redis."""
    assert n > 0 or n == -1, f"{n=}"
    # n=1 should return one item
    endRange: int = n - 1
    # endRange: int = n

    # TODO: what if None and n=1?
    await rem_none_items(client, items_key)

    res: List[str] = await client.lrange(items_key, 0, endRange)

    items: List[ScrapeItem] = [json.loads(i) for i in res]
    items = [i for i in items if i is not None]

    return items


async def get_scrape_items(
    client: aioredis.Redis,
    items_key: str,
    jl_file: Path,
    data_source: DataSourceScrapeItems,
    n: int,
) -> List[ScrapeItem]:
    """Get scrape_items from data source."""
    match data_source:
        case DataSourceScrapeItems.redis:
            res: List[ScrapeItem] = await get_redis_scrape_items(client, items_key, n=n)

        case DataSourceScrapeItems.jl_file:
            res = read_scrape_items_from_file(jl_file)
            if n is not None:
                res = res[:n]

        case other:
            raise NotImplementedError(f"{other=}")

    logger.info(f"read {len(res):,} items from {data_source.name}")

    # items: List[ScrapeItem] = [UrlRecord(**i) for i in res]

    return res


async def pop_scrape_items(
    client: aioredis.Redis, items_key: str, n: int
) -> Optional[List[ScrapeItem]]:
    """Pop scrape items from redis list.

    `n` is required so that new incoming items are not deleted
    """
    # TODO: however, items can be of any type, so now only works for scrapers that put one type of data in
    # `redis_items_key`
    # keep popping till not null item is found
    res: Optional[List[str]] = await client.lpop(items_key, n)

    if res is None:
        return None

    ITEMS: str = "item" if len(res) == 1 else "items"
    logger.debug(f"popped {len(res):,} {ITEMS} from `{items_key}`")

    items: List[ScrapeItem] = [json.loads(i) for i in res]
    items = [i for i in items if i is not None]

    return items


async def push_scrape_item(
    client: aioredis.Redis, items_key: str, item: dict, noPriority=False
) -> None:
    """Push scrape_item to redis list.

    Normally this happens in side scraper, but for testing purposes this method
    is also neccesary
    """
    try:
        json_str: str = json.dumps(item)
    except json.JsonEncodeError:
        logger.error(f"cannot encode json. {item=}")
        raise

    if noPriority:
        await client.rpush(items_key, json_str)
        return

    await client.lpush(items_key, json_str)


async def dump_scrape_items(
    redis_pool, items_key: str, jl_file: Path, n: int = 100
) -> None:
    """Dump scrape_items from redis to .jl file.

    Usage:
        import asyncio
        from scrape_utils.core.redis_connection import get_redis_pool
        from scrape_utils.models.redis.helpers import dump_scrape_items
        redis_pool = get_redis_pool()
        asyncio.run(dump_scrape_items(redis_pool))
    """
    async with redis_connection(redis_pool) as client:
        data: List[dict] = await get_scrape_items(
            client,
            items_key,
            jl_file=jl_file,
            data_source=DataSourceScrapeItems.redis,
            n=n,
        )

    write_scrape_items_to_jl(data, file=jl_file)


# SCRAPE_ITEMS_FILE
def write_scrape_items_to_jl(
    data: List[ScrapeItem],
    file: Path,
) -> None:
    """Write scrape_items to .jl file."""
    logger.info(f"writing {len(data):,} lines to file {file=}")
    with open(file, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")


# SCRAPE_ITEMS_FILE
def read_scrape_items_from_file(file: Path) -> List[ScrapeItem]:
    """Read from scrape_items file."""
    if not os.path.exists(file):
        raise FileNotFoundError(f"{file=} not found.")

    with open(file, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


############################
#### general redis methods
############################


async def delete_redis_keys(client: aioredis.Redis, keys: Optional[List[str]] = None):
    """Delete list of keys in redis."""
    # delete all keys
    if keys is None:
        logger.warning("deleting KEYS keys")
        keys = await client.keys("*")

    for key in keys:
        await client.delete(key)

    logger.warning(f"deleted {len(keys):,} keys")

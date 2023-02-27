"""helpers.py.

Helper methods for Redis HTTP cache implementation
"""
import logging
import pickle
from datetime import datetime
from pathlib import Path
from random import sample
from time import time
from typing import Final, List, Optional

import lz4.block as lz4  # type: ignore[import]
import redis
from scrapy.http import Response  # type: ignore[import]
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from yapic import json  # type: ignore[import]

from ..core.db import get_async_session
# from ..core.settings import START_URLS_KEY
from ..models.cache import HttpCacheItem
from ..models.cache.crud import CacheCRUD
from ..models.redis import SitemapRecord
from ..utils import get_create_event_loop

logger = logging.getLogger(__name__)

loop = get_create_event_loop()


# settings.data_dir
def save_response_to_file(response: Response, data_dir: str) -> None:
    page_path = Path(data_dir) / "page.html"
    with open(page_path, "wb") as html_file:
        logger.error(f"writing to {html_file=}")
        html_file.write(response.body)


def make_cache_item(response: Response) -> HttpCacheItem:
    # TODO: implement as HttpCacheItem.from_json
    time: Final[float] = datetime.utcnow().timestamp()

    data = {
        "status": response.status,
        "url": response.url,
        "headers": dict(response.headers),
        "body": response.body,
        "time": time,
    }

    return HttpCacheItem(**data)


# settings.db_async_connection_str
def save_compressed_response_pg(response: Response, async_connection_str: str) -> None:
    """Save / upsert compressed http response to postgres."""
    # using CRUD is safest

    async def inner() -> None:
        async_session: AsyncSession = get_async_session(async_connection_str)
        async with async_session() as session:
            cache_crud = CacheCRUD(session)

            cache_item: HttpCacheItem = HttpCacheItem.from_response(response)

            await cache_crud.upsert(cache_item)

    loop.run_until_complete(inner())


# settings.redis_http_cache_key
# settings.redis_http_date_key
def save_compressed_response_redis(
    client: redis.StrictRedis,
    http_cache_key: str,
    http_date_key: str,
    response: Response,
) -> None:
    """Save compressed http response to redis hset."""
    # TODO: optionally saving multiple strings as block saves more data
    # similar to what you did with Rarc

    # TODO: use composite hash? url + scrape date for instance
    url: Final[str] = response.url

    cache_item: HttpCacheItem = make_cache_item(response)
    compr_response: bytes = compress_response(cache_item)

    # always save cache and timestamp together
    client.hset(http_cache_key, response.url, compr_response)
    client.zadd(http_date_key, {url: time})


# settings.redis_http_cache_key
def move_cache(
    client_from: redis.StrictRedis,
    client_to: redis.StrictRedis,
    http_cache_key: str,
    n: int = -1,
    random: bool = True,
) -> None:
    """Move cache to another redis database.

    So the scraper can run in test move from this cache,
    and user can verify if everything works correctly,
    without affecting production database

    Example usage:
        from scrape_utils.cache.helpers import move_cache, populate_start_urls_from_redis_cache
        import redis
        from scrape_utils import settings
        client_from = redis.from_url(settings.redis_url)
        new_url = settings.redis_url[:-1] + '5'
        client_to =redis.from_url(new_url)
        # move_cache(client_from, client_to, n=100, random=True)

        # later
        populate_start_urls_from_redis_cache(client_to)
    """
    all_keys: List[str] = client_from.hkeys(http_cache_key)

    assert n < len(all_keys)
    if random:
        all_keys = sample(all_keys, n)

    cache_items = client_from.hmget(http_cache_key, all_keys)
    logger.info(f"got {len(cache_items):,} cache_items")

    client_to.hmset(http_cache_key, dict(zip(all_keys, cache_items)))


# settings.redis_http_cache_key
# START_URLS_KEY
def populate_start_urls_from_redis_cache(
    client: redis.StrictRedis, http_cache_key: str, start_urls_key: str
):
    """Populate start_urls from cache."""
    all_keys: List[str] = client.hkeys(http_cache_key)
    data = client.hmget(http_cache_key, all_keys)

    res: List[Optional[HttpCacheItem]] = [decompress_response(item) for item in data]
    cache_items: List[Optional[HttpCacheItem]] = [
        item for item in res if item is not None
    ]

    for cache_item in cache_items:
        try:
            item: dict = {"url": cache_item.url}
        except Exception as e:
            logger.info(f"{cache_item=}")
            raise

        client.rpush(start_urls_key, json.dumps(item))


def get_start_urls_from_pg_cache(
    session, limit: Optional[int] = None
) -> List[SitemapRecord]:
    """Get start urls from postgres cache."""
    query = select(HttpCacheItem.url)
    if limit is not None:
        query = query.limit(limit)

    res = session.execute(query).scalars()
    now = datetime.utcnow()
    # return list(res.fetchall())
    return [SitemapRecord(lastmod=now, url=i) for i in res.fetchall()]


def _compress(item):
    return lz4.compress(item)


def compress_response(cache_item: HttpCacheItem) -> bytes:
    return _compress(pickle.dumps(cache_item, protocol=4))


def decompress_response(compr_response: bytes) -> HttpCacheItem:
    item: HttpCacheItem | dict = pickle.loads(lz4.decompress(compr_response))
    # TODO: old api still holds plain dictionaries, support both for now
    # remove this later
    if isinstance(item, dict):
        if "time" not in item:
            item["time"] = time() - 86400
        return HttpCacheItem(**item)
    return item


# settings.redis_http_cache_key
def load_compressed_responses_redis(
    client: redis.StrictRedis, http_cache_key: str, url: Optional[str]
) -> List[HttpCacheItem]:
    """Load compressed responses.

    If `url` is passed, fetches for one url, if `url` is None, fetches all items
    """
    keys: List[str] = []
    if url is None:
        keys = client.hkeys(http_cache_key)
    else:
        keys = [url]

    res = client.hmget(http_cache_key, keys)
    # cache_items: List[bytes] =

    cache_items: List[Optional[HttpCacheItem]] = [
        item for item in res if item is not None
    ]

    return [decompress_response(compr_response) for compr_response in cache_items]


# settings.redis_http_cache_key
def load_compressed_response_redis(
    client: redis.StrictRedis, http_cache_key: str, url: str
) -> Optional[HttpCacheItem]:
    """Load compressed http response from redis hset by url."""
    # TODO: optionally saving multiple strings as block saves more data
    # similar to what you did with Rarc

    # TODO: use composite hash? url + scrape date for instance
    key: Final[str] = http_cache_key

    # compr_response: Optional[bytes] = client.hget(key, url)

    compr_responses = load_compressed_responses_redis(client, http_cache_key, url=url)
    # logger.error(f"{compr_responses=}")

    if len(compr_responses) != 1 or compr_responses[0] is None:
        logger.debug(f"{url=} does not exist in redis HSET `{key}`")
        return None

    return compr_responses[0]

    # return decompress_response(compr_response)


def load_compressed_response_pg(session, url: str) -> Optional[HttpCacheItem]:
    """Load compressed http response to postgres."""
    # compr_response = make_compressed_response(response)

    # session.filter()

    # async def inner() -> None:
    #     async_session: AsyncSession = get_async_session()
    #     async with async_session() as session:
    #         cache_crud = CacheCRUD(session)

    #         cache_item: HttpCacheItem = HttpCacheItem.from_response(response)

    #         return await cache_crud.get(url)

    # return loop.run_until_complete(inner)

    query = select(HttpCacheItem).where(HttpCacheItem.url == url)
    res = session.execute(query)
    r = res.one_or_none()

    if r is not None:
        return r[0]

    return None


def delete_oldest_cache():
    """Delete oldest cache.

    Delete oldest N rows from cache. First request urls, then delete
    """
    # TODO: add test for this method
    raise NotImplementedError

import logging
from typing import AsyncGenerator, Final

import redis
from redis import asyncio as aioredis

from .. import settings
from .settings import DECODE_RESPONSES, MAX_REDIS_CONNECTIONS

logger = logging.getLogger(__name__)


def get_redis_pool() -> aioredis.ConnectionPool:
    """Create async redis connection pool."""
    logger.info(f"using {settings.redis_url=}")
    return aioredis.ConnectionPool.from_url(
        settings.redis_url, decode_responses=DECODE_RESPONSES
    )


# async def redis_connection(redis_pool=None) -> AsyncGenerator[aioredis.Redis, None]:
def redis_connection(redis_pool: aioredis.ConnectionPool) -> aioredis.Redis:
    return aioredis.Redis(
        connection_pool=redis_pool, max_connections=MAX_REDIS_CONNECTIONS
    )

    # async with aioredis.Redis(  # type: ignore[var-annotated]
    #     connection_pool=redis_pool, max_connections=MAX_CONNECTIONS
    # ) as client:
    #     # yield client
    #     return client


def blocking_redis_connection() -> redis.StrictRedis:
    r: redis.StrictRedis = redis.from_url(
        settings.redis_url, decode_responses=DECODE_RESPONSES
    )
    return r

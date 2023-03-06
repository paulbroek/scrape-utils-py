"""redis_connection.py.

Redis connection methods
"""

import logging

import redis
from redis import asyncio as aioredis

from .settings import DECODE_RESPONSES, MAX_REDIS_CONNECTIONS_DEFAULT

# from typing import AsyncGenerator


logger = logging.getLogger(__name__)


def get_redis_pool(redis_url: str) -> aioredis.ConnectionPool:
    """Create async redis connection pool."""
    logger.info(f"using {redis_url=}")
    return aioredis.ConnectionPool.from_url(
        redis_url, decode_responses=DECODE_RESPONSES
    )


# async def redis_connection(redis_pool=None) -> AsyncGenerator[aioredis.Redis, None]:
def redis_connection(
    redis_pool: aioredis.ConnectionPool,
    max_connections: int = MAX_REDIS_CONNECTIONS_DEFAULT,
) -> aioredis.Redis:
    """Create async redis connection."""
    return aioredis.Redis(connection_pool=redis_pool, max_connections=max_connections)

    # async with aioredis.Redis(  # type: ignore[var-annotated]
    #     connection_pool=redis_pool, max_connections=MAX_CONNECTIONS
    # ) as client:
    #     # yield client
    #     return client


def blocking_redis_connection(
    redis_url: str, decode_responses: bool = DECODE_RESPONSES
) -> redis.StrictRedis:
    """Create blocking redis connection."""
    r: redis.StrictRedis = redis.from_url(redis_url, decode_responses=decode_responses)  # type: ignore[call-overload]
    return r

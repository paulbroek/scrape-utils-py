import logging
from abc import ABC, abstractmethod

from redis import asyncio as aioredis
from yapic import json

from ...core.config import ScrapeSettings
from ...core.settings import DECODE_RESPONSES, MAX_REDIS_CONNECTIONS_DEFAULT

logger = logging.getLogger(__name__)


# class RedisManagerABC(ABC, Generic[ModelType]):
class RedisManagerABC(ABC):
    # @abstractmethod
    # async def connect(self) -> Coroutine:
    #     pass

    pass

    # @abstractmethod
    # async def push_to_scrape(self, items_key: str, dict: dict, **kwargs) -> Coroutine:
    #     pass

    # @abstractmethod
    # async def get(self, model_id: str | UUID) -> ModelType:
    #     pass


# class BaseRedisManager(RedisManagerABC, Generic[ModelType]):
class BaseRedisManager(RedisManagerABC):
    def __init__(self, settings: ScrapeSettings) -> None:
        self.settings = settings
        self._client = self.__get_client()

    def __get_connection_pool(self):
        return aioredis.ConnectionPool.from_url(
            self.settings.redis_url, decode_responses=DECODE_RESPONSES
        )

    def __get_client(self) -> aioredis.Redis:
        redis_pool = self.__get_connection_pool()
        return aioredis.Redis(
            connection_pool=redis_pool, max_connections=MAX_REDIS_CONNECTIONS_DEFAULT
        )

    async def _push_list_item(
        self, items_key: str, item: dict, noPriority=False
    ) -> None:
        """Push (scrape) item to redis list.

        Normally this happens inside scraper
        Can be used for API / testing or custom scraper
        """
        assert isinstance(item, dict), f"{type(item)=}"
        try:
            json_str: str = json.dumps(item)
        except json.JsonEncodeError:
            logger.error(f"cannot encode json. {item=}")
            raise

        if noPriority:
            await self._client.rpush(items_key, json_str)
            return

        await self._client.lpush(items_key, json_str)

    # async def push_to_scrape(self, items_key: str, item: dict, **kwargs) -> None:
    #     await self.push_list_item(items_key, item, **kwargs)

    async def _nlist_item(self, list_key: str) -> int:
        """Return length of redis list item."""
        return await self._client.llen(list_key)

    ##################
    #### HSET methods
    ##################

    async def _is_set_member(self, set_key: str, set_member_key: str) -> bool:
        """Return if `set_member_key` is member of redis hset."""
        return await self._client.hexists(set_key, set_member_key)

    async def _add_set_member(
        self, set_key: str, set_member_key: str, value: str
    ) -> int:
        assert isinstance(value, str), f"{type(value)=}"
        return await self._client.hset(set_key, set_member_key, value)

    async def _get_set_member(self, set_key: str, set_member_key: str) -> str | None:
        return await self._client.hget(set_key, set_member_key)

    async def _del_set_member(self, set_key: str, set_member_key: str) -> int:
        return await self._client.hdel(set_key, set_member_key)


class ScrapeRedisManager(BaseRedisManager):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    ################
    ### START URLS
    ################

    async def push_to_scrape(self, item: dict, **kw) -> None:
        return await self._push_list_item(
            self.settings.redis_start_urls_key, item, **kw
        )

    async def nstart_url(self) -> int:
        return await self._nlist_item(self.settings.redis_start_urls_key)

    ##################
    ### SCRAPE ITEMS
    ##################

    async def push_item(self, item: dict, **kw) -> None:
        return await self._push_list_item(self.settings.redis_items_key, item, **kw)

    async def nscrape_item(self) -> int:
        return await self._nlist_item(self.settings.redis_items_key)

    #########################
    ### VERIFY SCRAPE ITEMS
    #########################

    async def is_verify_scraped_member(self, member_key: str) -> bool:
        return await self._is_set_member(
            self.settings.redis_verify_scraped_key, member_key
        )

    async def add_verify_scraped(self, key: str, value: dict) -> int:
        return await self._add_set_member(
            self.settings.redis_verify_scraped_key, key, json.dumps(value)
        )

    async def get_verify_scraped(self, key: str) -> str | None:
        return await self._get_set_member(self.settings.redis_verify_scraped_key, key)

    async def del_verify_scraped(self, key: str) -> int:
        return await self._del_set_member(self.settings.redis_verify_scraped_key, key)

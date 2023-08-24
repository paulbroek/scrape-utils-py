import logging
from abc import ABC, abstractmethod
from typing import Coroutine

from redis import asyncio as aioredis
from yapic import json

from ...core.config import MyBaseSettings
from ...core.settings import DECODE_RESPONSES, MAX_REDIS_CONNECTIONS_DEFAULT

logger = logging.getLogger(__name__)


# class RedisManager(ABC):
# class RedisManager:
#     def __init__(self, client: aioredis.Redis) -> None:
#         self.client = client

#     async def push_list_item(
#         self, items_key: str, item: dict, noPriority=False
#     ) -> None:
#         """Push (scrape) item to redis list.

#         Normally this happens inside scraper
#         Can be used for API / testing or custom scraper
#         """
#         assert isinstance(item, dict), f"{type(item)=}"
#         try:
#             json_str: str = json.dumps(item)
#         except json.JsonEncodeError:
#             logger.error(f"cannot encode json. {item=}")
#             raise

#         if noPriority:
#             await self.client.rpush(items_key, json_str)
#             return

#         await self.client.lpush(items_key, json_str)

#     async def push_to_scrape(self, item: dict, noPriority=False) -> False:
#         await self.push_list_item()


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


# class RedisManagerABC(ABC, Generic[ModelType]):
#     """RedisManager ABC skeleton class."""

#     # model: Optional[Type[ModelType]] = None

#     def __init__(self, session: AsyncSession, upsertKey: str) -> None:
#         self.session: AsyncSession = session
#         # logger.info(f"{dir(self.model)=}")
#         # assert hasattr(
#         #     model, upsertKey
#         # ), f"{upsertKey=} not in {model=}. Use a different upsertKey"
#         self.upsertKey: str = upsertKey
#         self._cached_patch_model = self._get_patch_model()

#     # TODO: make this work with class variable: `model`, set in events.crud
#     # dynamically determine the PatchType
#     @classmethod
#     def _get_patch_model(cls) -> Type:
#         model_name = cls.model.__name__
#         module_name = cls.model.__module__
#         patch_model_name = f"{model_name}Patch"
#         patch_module = importlib.import_module(module_name)
#         try:
#             PatchModel = getattr(patch_module, patch_model_name)
#         except AttributeError:
#             logger.error(f"please implement `{patch_model_name}` for {module_name}")
#             raise

#         return PatchModel

#     @property
#     def PatchModel(self) -> Type:
#         # if not hasattr(self, "_cached_patch_type"):
#         #     self._cached_patch_model = self._get_patch_model()
#         return self._cached_patch_model

#     @abstractmethod
#     async def create(self, data: CreateType) -> ModelType:
#         pass

#     @abstractmethod
#     async def get(self, model_id: str | UUID) -> ModelType:
#         pass

#     @abstractmethod
#     async def patch(self, model_id: str | UUID, data: PatchType) -> ModelType:
#         pass

#     @abstractmethod
#     async def upsert(self, data: CreateType) -> ModelType:
#         pass

#     @abstractmethod
#     async def delete(self, model_id: str | UUID) -> bool:
#         pass


# class BaseRedisManager(RedisManagerABC, Generic[ModelType]):
class BaseRedisManager(RedisManagerABC):
    # def __init__(self, client: aioredis.Redis, settings: MyBaseSettings) -> None:
    def __init__(self, settings: MyBaseSettings) -> None:
        # self.client = client
        self.settings = settings
        self.client = self._get_client()

    def _get_connection_pool(self):
        return aioredis.ConnectionPool.from_url(
            self.settings.redis_url, decode_responses=DECODE_RESPONSES
        )

    def _get_client(self) -> aioredis.Redis:
        redis_pool = self._get_connection_pool()
        return aioredis.Redis(
            connection_pool=redis_pool, max_connections=MAX_REDIS_CONNECTIONS_DEFAULT
        )

    async def push_list_item(
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
            await self.client.rpush(items_key, json_str)
            return

        await self.client.lpush(items_key, json_str)

    # async def push_to_scrape(self, items_key: str, item: dict, **kwargs) -> None:
    #     await self.push_list_item(items_key, item, **kwargs)

    async def nlist_item(self, list_key: str) -> int:
        """Return length of redis list item."""
        return await self.client.llen(list_key)

    async def is_set_member(self, set_key: str, set_member_key: str) -> bool:
        """Return if `set_key` is member of redis hset."""
        return await self.client.sismember(set_key, set_member_key)

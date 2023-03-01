"""main.py.

Fetching data from redis to db

Scrape items are pulled from redis, put to queue, consumed by workers, 
the individual scrape project's scripts/redis_to_pg.py will implement `process_queue` to send processed data to pg
"""

import asyncio
import logging
from typing import Callable, Generic, List, Optional

from ....core.redis_connection import get_redis_pool, redis_connection
from ....types import ScrapeItemType
from ....utils import get_create_event_loop
from ...redis.helpers import pop_scrape_items, push_scrape_item

loop = get_create_event_loop()

logger = logging.getLogger(__name__)


class FetchApp(Generic[ScrapeItemType]):
    def __init__(
        self,
        redis_url: str,
        items_key: str,
        process_queue_callback: Callable,
        fetch_delay: float = 0.1,
        nworker: int = 10,
        log_interval: int = 15,
        max_queue_len: int = 2000,
    ) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.redis_pool = get_redis_pool(redis_url)

        # item processing parameters
        self.items_key = items_key
        self.process_queue_callback = process_queue_callback
        self.fetch_delay = fetch_delay
        self.nworker = nworker

        # monitoring parameters
        self.log_interval = log_interval
        self.max_queue_len = max_queue_len

    async def _to_queue(self, item: dict) -> None:
        """Put ScrapeItem to queue."""
        assert isinstance(item, dict), f"{type(item)=}"
        # logger.info(f"{item=}")
        await self.queue.put(item)

    async def _fetch_scrape_items(self) -> None:
        """Fetch scrape items from redis.

        Make sure to tweak `delay` to a level where redis list does not get depleted. Or other workers have nothing to do
        And in case of failure, all items are gone
        """
        # 1. get item from redis
        while True:
            async with redis_connection(self.redis_pool) as client:
                # items: List[ScrapeItemType] = await pop_scrape_items(
                items: Optional[List[dict]] = await pop_scrape_items(
                    client, self.items_key, n=1
                )

                if items is None or len(items) == 0:
                    logger.debug("received no or `null` item")
                    await asyncio.sleep(0.01)
                    continue

                # item: Optional[ScrapeItemType] = items[0]
                item: Optional[dict] = items[0]
                if item is None:
                    continue

                logger.info(
                    f"got '{item['type']}' item from redis. url={item['item']['url']}"
                )

            # 2. add item to queue
            # await queue.put(item)
            await self._to_queue(item)

            # 3. delay before fetching the next item
            await asyncio.sleep(self.fetch_delay)

    async def _get_all_items(self):
        """Get all items from asyncio queue."""
        items = []
        while self.queue.qsize() > 0:
            item = await self.queue.get()
            items.append(item)
            self.queue.task_done()
        return items

    async def _log_queue_len(self) -> None:
        """Log the length of queue periodically."""
        while True:
            queue_len: int = self.queue.qsize()
            logger.warning(f"Queue length: {queue_len:,}")

            # for now, let program exit when maxLen is exceeded
            if queue_len > self.max_queue_len:
                # push items back to redis list first
                items = await self._get_all_items()
                async with redis_connection(self.redis_pool) as client:
                    cors = [
                        push_scrape_item(client, self.items_key, item) for item in items
                    ]
                    await asyncio.gather(*cors)
                logger.info(f"pushed {len(items):,} queue items back to redis list")

                raise Exception(f"{queue_len=} > {self.max_queue_len}")

            await asyncio.sleep(self.log_interval)

    async def continuous_fetch_app(self) -> None:
        """Other than _main this app fetches scrape_items one by one, upserts to pg, and removes from list if succesful."""
        # start fetching items in the background
        fetch_task = asyncio.create_task(self._fetch_scrape_items())

        # process items in the queue
        tasks = []
        # create `nworker` coroutines to process the queue
        for _ in range(self.nworker):
            task = asyncio.create_task(self.process_queue_callback(self.queue))
            tasks.append(task)

        # log the length of the queue periodically
        log_task = asyncio.create_task(self._log_queue_len())

        # wait for all tasks to complete
        await asyncio.gather(fetch_task, *tasks, log_task)

    def run(self) -> None:
        """Run the fetch app."""
        loop.run_until_complete(self.continuous_fetch_app())

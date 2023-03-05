"""populate_redis.py.

Poulate redis with starting urls to scrape

Optionally remove all existing items from redis, and push a list of new urls,
so that the scraper will start running

Sitemap:
    - events are in: https://www.meetup.com/events-index-sitemap.xml
    - visit https://www.meetup.com/sw_events_1.xml.gz and extract
    - stored in ./data dir

Usage:
    py311
    # fetches urls from data/sw_events_1.xml with a random sample
    ipy ./scrape_meetup/scripts/populate_redis.py -i -- --data_source sitemap -n100
    ipy ./scrape_meetup/scripts/populate_redis.py -i -- --data_source sitemap
    ipy ./scrape_meetup/scripts/populate_redis.py -i -- --data_source redis -n1000 --dryrun

    # fetches custom urls from data/scrape_urls.jl
    ipy ./scrape_meetup/scripts/populate_redis.py -i --

    # do not delete keys in redis (not recommended)
    ipy ./scrape_meetup/scripts/populate_redis.py -i -- --no_delete

    # OR run as module
    pi ~/repos/misc-scraping/misc_scraping/scrape_meetup
    python -m scrape_meetup.scripts.populate_redis --from_sitemap -n1000

    # OR using Docker + make
    make populate_redis

    !!! if you get OSError due to too many openfiles == open connections, increase ulimit as follows:
    ulimit -n 10000
    # see current limit
    ulimit -Sn
"""

import asyncio
import importlib
import logging
from pathlib import Path
from typing import Final, List, Optional

import typer
from dotenv import load_dotenv
from rarc_utils.log import get_create_logger
from redis import asyncio as aioredis
from scrape_utils.core.config_env_file import ENV_FILE
from scrape_utils.core.redis_connection import get_redis_pool, redis_connection
from scrape_utils.db.helpers import filter_only_new_start_urls
from scrape_utils.models.redis import (CollectionBase, DataSourceUrls,
                                       SitemapRecord)
from scrape_utils.models.redis.helpers import (delete_redis_keys,
                                               get_scrape_urls_from_source,
                                               push_redis_to_scrape)
from scrape_utils.utils import chunked_list, get_create_event_loop
from scrape_utils.utils.typer import collection_validator

# it already loaded in scrape_meetup main module
load_dotenv(ENV_FILE)
app = typer.Typer(pretty_exceptions_short=False)
loop = get_create_event_loop()

logger = get_create_logger(cmdLevel=logging.INFO, color=1)

MAX_BATCH_SIZE: Final[int] = 2_000
MAX_CONNECTIONS: Final[int] = 100

# KEYS_TO_DELETE: Final[List[str]] = [
#     "rspider:dupefilter",
#     "rspider:start_urls",
#     "rspider:items",
# ]
# KEYS_TO_DELETE: Final[List[str]] = [
#     "rspider:dupefilter",
#     "rspider:start_urls",
# ]
KEYS_TO_DELETE: Final[List[str]] = [
    "rspider:start_urls",
]
# TODO: use regex for matching keys to delete?
# TODO: ideally you do not want to delete dupefilter, or worker scrapers start doing repetitive work.


@app.command()
def main(
    library_name: str = typer.Option(...),
    collection_member: str = typer.Option(...),
    no_delete: bool = typer.Option(
        False,
        "--no_delete",
        help="do not delete all keys in redis",
    ),
    data_source: DataSourceUrls = typer.Option(
        DataSourceUrls.redis,
        "--data_source",
        help="Data source to fetch sitemap urls from",
    ),
    random: bool = typer.Option(
        False,
        "--random",
        help="take random sample from sitemap urls",
    ),
    filter_missing: bool = typer.Option(
        False,
        "--filter_missing",
        help="only push urls that are missing in pg",
    ),
    filter_only_new: bool = typer.Option(
        False,
        "--filter_only_new",
        help="only push urls with lastmod later than created_at",
    ),
    maxn: Optional[int] = typer.Option(
        None,
        "--maxn",
        "-n",
        help="max items to keep from sitemap.xml",
    ),
    dryrun: bool = typer.Option(
        False,
        "--dryrun",
        help="only get data, do not push to redis",
    ),
):
    """Implement main app."""
    # load setting modules dynamically
    try:
        library = importlib.import_module(library_name)
    except ModuleNotFoundError:
        logger.error("please pass valid base library to import")
        return

    settings = library.settings
    settings_module = importlib.import_module(f"{library_name}.core.settings")

    redis_pool: aioredis.ConnectionPool = get_redis_pool(settings.redis_url)

    DATA_PATH: Final[Path] = Path(settings.data_dir)
    SCRAPE_URLS_FILE: Final[Path] = DATA_PATH / "scrape_urls.jl"
    # SCRAPE_ITEMS_FILE: Final[Path] = DATA_PATH / "scrape_items.jl"

    EVENTS_SITEMAP_XML_FILE: Final[Path] = DATA_PATH / "sw_events_1.xml"

    MAKE_SINGULAR: Final[bool] = getattr(
        settings_module, "SITEMAP_KEY_MAKE_SINGULAR", False
    )

    collection: CollectionBase = collection_validator(library_name, collection_member)

    async def _main() -> Optional[List[SitemapRecord]]:
        """Implement async main loop."""
        scrape_urls: List[SitemapRecord] = await get_scrape_urls_from_source(
            redis_pool,
            data_source=data_source,
            db_connection_str=settings.db_connection_str,
            scrape_urls_file=SCRAPE_URLS_FILE,
            events_sitemap_xml_file=EVENTS_SITEMAP_XML_FILE,
            random=random,
            maxn=maxn,
            collection=collection,
            collection_as_singular=MAKE_SINGULAR,
            reverse=False,
        )

        logger.warning(f"{scrape_urls[:5]=}")

        if filter_only_new:
            scrape_urls = filter_only_new_start_urls(
                settings.db_connection_str, scrape_urls, table=collection_member
            )

        if filter_missing and not filter_only_new:
            # TODO: load instance dynamically? or?
            # class loads from different paths. Hmm.
            # scrape_urls = filter_existing_start_urls(
            #     settings.db_connection_str, scrape_urls, model=Event
            # )
            raise NotImplementedError

        if dryrun:
            logger.warning("exiting, since dryrun=True")
            return scrape_urls

        # 'else': push all sitemap events to redis

        batches = chunked_list(scrape_urls, MAX_BATCH_SIZE)

        async with redis_connection(redis_pool) as client:
            # optionally delete all keys in redis
            if not no_delete:
                await delete_redis_keys(client, KEYS_TO_DELETE)

            for ix, scrape_urls_batch in enumerate(batches, start=1):
                logger.info(f"batch {ix} / {len(batches)}")
                # logger.info(f"{scrape_urls_batch[:2]=}")

                # CAUTION: limit number of active open files using ulimit, see top of file
                tasks = [
                    push_redis_to_scrape(client, item) for item in scrape_urls_batch
                ]
                # semaphore = asyncio.BoundedSemaphore(500)
                await asyncio.gather(*tasks)
                # async with semaphore:
                #     await asyncio.gather(*tasks)

                logger.info(f"pushed {len(scrape_urls_batch):,} items")

        return scrape_urls

    return loop.run_until_complete(_main())


if __name__ == "__main__":
    app()

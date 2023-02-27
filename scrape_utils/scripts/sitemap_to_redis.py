"""sitemap_to_redis.py.

Get all sitemap files of certain type, parse them and save to redis list

Usage:
    py311
    # fetches urls from data/sw_events_1.xml with a random sample
    SCRAPE_LIBRARY=...
    ipy ./scrape_utils/scripts/sitemap_to_redis.py -i -- --library-name $SCRAPE_LIBRARY --collection events -n5
    ipy ./scrape_utils/scripts/sitemap_to_redis.py -i -- --library-name $SCRAPE_LIBRARY --collection groups
    ipy ./scrape_utils/scripts/sitemap_to_redis.py -i -- --library-name $SCRAPE_LIBRARY --collection events 

    # OR run as module
    pi ~/repos/misc-scraping/misc_scraping/scrape_utils
    python -m scrape_utils.scripts.sitemap_to_redis

    # OR using Docker + make
    make sitemap_to_redis

    !!! if you get OSError due to too many openfiles == open connections, increase ulimit as follows:
    ulimit -n 10000
    # see current limit
    ulimit -Sn
"""

import asyncio
import importlib
import logging
from typing import Final, List, Optional

import pandas as pd
import typer
from rarc_utils.log import get_create_logger
from redis import asyncio as aioredis
from scrape_utils.core.redis_connection import get_redis_pool, redis_connection
from scrape_utils.models.redis import CollectionBase, SitemapRecord
from scrape_utils.models.redis.helpers import (delete_sitemap_key,
                                               parse_unzip_url,
                                               push_sitemap_record_to_redis,
                                               read_sitemap_base,
                                               sitemap_record_from_row)
from scrape_utils.utils import chunked_list, get_create_event_loop

app = typer.Typer(pretty_exceptions_short=False)
loop = get_create_event_loop()

logger = get_create_logger(
    cmdLevel=logging.INFO,
    color=1,
)

DataFrameOrNone = Optional[pd.DataFrame]
MAX_BATCH_SIZE: Final[int] = 2_000


def collection_validator(library_name: str, collection_member: str) -> CollectionBase:
    """Import collection dynamically from custom package."""
    try:
        redis_module = importlib.import_module(f"{library_name}.models.redis")
    except ModuleNotFoundError:
        raise typer.BadParameter(
            f"{library_name} has no `models.redis.Collection` class"
        )

    collection_class = redis_module.Collection

    try:
        collection = getattr(collection_class, collection_member)
    except AttributeError:
        raise typer.BadParameter(
            f"{collection_class=} has no attribute `{collection_member}`. available members: {list(collection_class.__members__)}"
        )

    return collection


@app.command()
def main(
    library_name: str = typer.Option(...),
    collection_member: str = typer.Option(...),
    delete: bool = typer.Option(
        True,
        "--delete",
        help="delete sitemap in redis",
    ),
    maxn: Optional[int] = typer.Option(
        None,
        "--maxn",
        "-n",
        help="max sitemaps to scrape for given collection",
    ),
    maxrecs: Optional[int] = typer.Option(
        None,
        "--maxrecs",
        "-m",
        help="max records to push to redis",
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
    DOMAIN: str = settings_module.DOMAIN
    SITEMAP_FORMAT: str = settings_module.SITEMAP_FORMAT

    redis_pool: aioredis.ConnectionPool = get_redis_pool(settings.redis_url)

    collection: CollectionBase = collection_validator(library_name, collection_member)

    async def _main() -> Optional[List[SitemapRecord]]:
        """Implement main loop."""
        SITEMAP_URL: Final[str] = SITEMAP_FORMAT.format(
            domain=DOMAIN, collection=collection.name
        )

        res: DataFrameOrNone = read_sitemap_base(SITEMAP_URL)
        if res is None:
            logger.warning(f"{res=}")
            return None

        df: pd.DataFrame
        if maxn:
            df = res.head(maxn)
        else:
            df = res

        logger.info(f"will fetch {len(df):,} sitemap files from {DOMAIN}")

        # TODO: still some blocking code. after having fetched scrape urls, can start pushing urls to queue, which pushes to redis
        dfs = []
        for url in df["loc"]:
            new_df: DataFrameOrNone = parse_unzip_url(url)
            if new_df is not None:
                dfs.append(new_df)
                logger.info(f"got sitemap {url}")

        assert dfs

        final_df: pd.DataFrame = pd.concat(dfs, ignore_index=True).rename(
            columns={"loc": "url"}
        )

        final_df["lastmod"] = pd.to_datetime(
            final_df["lastmod"], infer_datetime_format=True
        )

        if maxrecs is not None:
            final_df = final_df.head(maxrecs)

        logger.info(
            f"got {len(final_df):,} `{collection.name}` sitemap urls from {DOMAIN}"
        )

        # sitemap_urls: List[SitemapRecord] = final_df.to_dict(orient="records").map(SitemapRecord)
        sitemap_urls: List[SitemapRecord] = final_df.apply(
            sitemap_record_from_row, axis=1
        ).to_list()
        batches = chunked_list(sitemap_urls, MAX_BATCH_SIZE)

        if dryrun:
            logger.warning("exiting, since dryrun=True")
            return sitemap_urls

        # push urls to scrape to redis
        async with redis_connection(redis_pool) as client:
            # optionally delete the sitemap key
            if delete:
                await delete_sitemap_key(client, collection)

            for ix, scrape_urls_batch in enumerate(batches, start=1):
                logger.info(f"batch {ix} / {len(batches)}")

                tasks = [
                    push_sitemap_record_to_redis(client, collection, record)
                    for record in scrape_urls_batch
                ]
                await asyncio.gather(*tasks)

                logger.info(f"pushed {len(scrape_urls_batch):,} items")

        return sitemap_urls

    return loop.run_until_complete(_main())


if __name__ == "__main__":
    app()

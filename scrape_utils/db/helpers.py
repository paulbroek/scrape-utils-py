"""helpers.py.

Helper methods for Event objects
"""
import logging
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from scrape_utils.core.db import get_engine
from scrape_utils.models.redis import SitemapRecord

logger = logging.getLogger(__name__)


def filter_only_new_start_urls(
    db_connection_str: str,
    start_urls: List[SitemapRecord],
    table: str,
    onlyFutureRows: bool = True,
) -> List[SitemapRecord]:
    """Filter out start urls, that with `lastmod` later than `created_at` ScrapeUpdate in pg."""
    # TODO: function works best if sitemaps also gets refreshed in redis! run `sitemap_to_redis`
    logger.warning(f"{start_urls[:3]=}")
    logger.info(f"start_urls before filtering: {len(start_urls):,}")

    # https://docs.sqlalchemy.org/en/14/errors.html#error-3o7r
    engine = get_engine(db_connection_str, future=False)
    # query: str = "SELECT uuid, url, updated_at, time_start FROM {table}".format(
    query: str = "SELECT uuid, url, updated_at FROM {table}".format(
        table=table
    )
    # if onlyFutureRows:
    #     query = "SELECT uuid, url, updated_at FROM {table} WHERE time_start > NOW()".format(table=table)
    # else:
    #     query =

    items_df = pd.read_sql(query, engine)

    logger.info(f"got {len(items_df):,} {table} rows from postgres")

    sitemap_df = pd.DataFrame(start_urls)
    # sitemap_df["lastmod"] = pd.to_datetime(sitemap_df.lastmod_ts, unit="s")

    last_24_hours: datetime = datetime.now() - timedelta(hours=24)
    recent_rows = sitemap_df[sitemap_df["lastmod"] >= last_24_hours]

    # nmodified: int = len(recent_rows)
    logger.info(f"{len(recent_rows):,} {table} pages were modified in last 24 hours")

    # merge/join the datasets, and include all sitemap items that are not in table
    merged_df = pd.merge(sitemap_df, items_df, on="url", how="left")
    # merged_df.sort_values('lastmod', inplace=True, ascending=False)

    # items_to_scrape = len(merged_df[merged_df['lastmod'] > merged_df['updated_at']])
    items_to_scrape = merged_df[
        (merged_df["updated_at"].isna())
        | (merged_df["lastmod"] > merged_df["updated_at"])
    ]
    # TODO: sort on future items, not easy, because so many null rows
    # nitems_to_scrape: int = len(items_to_scrape)
    # logger.info(f"{nitems_to_scrape=:,}")
    # optionally filter out items that lie in the past
    # print(f"head df: \n\n{items_to_scrape.head(25)}")
    # if onlyFutureRows:
    #     items_to_scrape = items_to_scrape[items_to_scrape.time_start < ]

    filtered_start_urls_records: List[dict] = items_to_scrape[
        ["url", "lastmod"]
    ].to_dict(orient="records")
    filtered_start_urls: List[SitemapRecord] = [
        SitemapRecord(**e) for e in filtered_start_urls_records
    ]

    # TODO: should actually also look at scrape urls already in redis, to prevent duplicate pushes
    # no, not needed, they get removed by redis automatically

    logger.info(f"start_urls after filtering: {len(filtered_start_urls):,}")

    return filtered_start_urls

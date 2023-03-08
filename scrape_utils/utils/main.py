"""main.py.

Main utilify functions for scrape-utils
"""
import asyncio
import logging
import resource

import numpy as np
import uvloop

from ..core.settings import REQUIRED_SOFT_ULIMIT

logger = logging.getLogger(__name__)


def get_create_event_loop():
    uvloop.install()
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


def chunked_list(lst: list, chunk_size: int):
    return np.array_split(
        np.array(lst), len(lst) // chunk_size + int(len(lst) % chunk_size != 0)
    )


def set_ulimit() -> None:
    # check if ulimit is not too low
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft_limit < REQUIRED_SOFT_ULIMIT:
        logger.warning(f"{soft_limit=:,} < {REQUIRED_SOFT_ULIMIT=:,}. Increasing it")
    # increase it
    resource.setrlimit(resource.RLIMIT_NOFILE, (REQUIRED_SOFT_ULIMIT, hard_limit))

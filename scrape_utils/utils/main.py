"""main.py.

Main utilify functions for scrape-utils
"""
import asyncio

import numpy as np


def get_create_event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


def chunked_list(lst: list, chunk_size: int):
    return np.array_split(
        np.array(lst), len(lst) // chunk_size + int(len(lst) % chunk_size != 0)
    )

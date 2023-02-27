import asyncio
from typing import Final, Tuple

# import aiohttp
import numpy as np
# import geocoder
import requests

MAPS_URL: Final[str] = "https://maps.googleapis.com/maps/api/geocode/json"

# hardcoded way
# def get_location(addr: str):
#     params = {"sensor": "false", "address": "Mountain View, CA"}
#     r = requests.get(MAPS_URL, params=params)
#     results = r.json()["results"]

#     location = results[0]["geometry"]["location"]
#     return location["lat"], location["lng"]


# def get_location_geocoder(addr: str) -> Tuple[float, float]:
#     """Get location using Geocoder."""
#     # TODO: library does no longer work
#     g = geocoder.google(addr)
#     return g.latlng


def get_create_event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


def chunked_list(lst: list, chunk_size: int):
    return np.array_split(
        np.array(lst), len(lst) // chunk_size + int(len(lst) % chunk_size != 0)
    )

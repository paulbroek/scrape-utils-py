from fastapi import APIRouter, Depends
from fastapi import status as http_status

from ....models.main import StatusMessage
from . import HttpCacheItem, HttpCacheItemPatch, HttpCacheItemRead
from .crud import CacheCRUD
from .dependencies import get_cache_crud

# from . import Event, EventCreate, EventPatch, EventRead


# router = APIRouter()
router = APIRouter(prefix="/cache", tags=["cache"])


# @router.post("", response_model=EventRead, status_code=http_status.HTTP_201_CREATED)
# async def create_event(
#     data: EventCreate, events: EventsCRUD = Depends(get_events_crud)
# ):
#     event = await events.create(data=data)

#     return event


@router.get(
    "/{cache_id}", response_model=HttpCacheItemRead, status_code=http_status.HTTP_200_OK
)
async def get_cache_by_uuid(cache_id: str, caches: CacheCRUD = Depends(get_cache_crud)):
    event = await caches.get(model_id=cache_id)

    return event

@router.get(
    "/{cache_id}", response_model=HttpCacheItemRead, status_code=http_status.HTTP_200_OK
)
async def get_cache_by_url(url: str, caches: CacheCRUD = Depends(get_cache_crud)):
    event = await caches.get(url=url)

    return event

# @router.patch(
#     "/{event_id}", response_model=EventRead, status_code=http_status.HTTP_200_OK
# )
# async def patch_event_by_uuid(
#     event_id: str, data: EventPatch, events: EventsCRUD = Depends(get_events_crud)
# ):
#     event: Event = await events.patch(model_id=event_id, data=data)

#     return event


@router.delete(
    "/{cache_id}", response_model=StatusMessage, status_code=http_status.HTTP_200_OK
)
async def delete_cache_by_uuid(
    cache_id: str, caches: CacheCRUD = Depends(get_cache_crud)
):
    status = await caches.delete(model_id=cache_id)

    return {"status": status, "message": "The cache has been deleted!"}

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db import get_async_session, yield_async_Session
from .crud import CacheCRUD


async def get_cache_crud(
    # session: AsyncSession = Depends(get_async_session)
    session: AsyncSession = Depends(yield_async_Session),
) -> CacheCRUD:
    return CacheCRUD(session=session)

import logging
from typing import List
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from . import ScrapeUpdate, ScrapeUpdateCreate

logger = logging.getLogger(__name__)


class ScrapeUpdatesCRUD:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: ScrapeUpdateCreate) -> ScrapeUpdate:
        assert isinstance(data, ScrapeUpdateCreate)
        values = data.dict()

        event = ScrapeUpdate(**values)
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)

        return event

    async def get(self, event_id: str | UUID) -> ScrapeUpdate:
        statement = select(ScrapeUpdate).where(ScrapeUpdate.uuid == event_id)
        results = await self.session.execute(statement=statement)
        item = results.scalar_one_or_none()  # type: ScrapeUpdate | None

        if item is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="The scrape_item hasn't been found!",
            )

        return item

    async def patch(self, event_id: str | UUID, data) -> ScrapeUpdate:
        raise NotImplementedError(
            "`patch()` not implemented for ScrapeUpdate, all updates should be unique"
        )

    async def delete(self, event_id: str | UUID) -> bool:
        raise NotImplementedError(
            "`delete()` not implemented for ScrapeUpdate, all updates should persist forever"
        )
        # statement = delete(Event).where(Event.uuid == event_id)

        # await self.session.execute(statement=statement)
        # await self.session.commit()

        # return True

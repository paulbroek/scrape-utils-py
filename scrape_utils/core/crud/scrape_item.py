"""scrape_item.py.

ScrapeItem CRUD class
"""
import logging
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from ...models.scrape.scrape_update import ScrapeUpdate
from ...types import CreateType, ModelType, PatchType
from . import BaseCRUD

logger = logging.getLogger(__name__)


class ScrapeItemCRUD(BaseCRUD):
    """ScrapeItemCRUD class that implements base functionality for CRUD operations of scrapeItem SQLModel models.

    ScrapeItems have different ways of patching: `nupdate` and `updated_at` get updated
    """

    def __init__(self, session: AsyncSession, upsertKey="url") -> None:
        super().__init__(session=session, upsertKey=upsertKey)

    async def patch(self, model_id: str | UUID, data: PatchType, **kwargs) -> ModelType:
        """Patch a scrape_item instance."""
        # logger.info(f"{model_id=}")
        instance: ModelType = await self.get(model_id=model_id)
        values = data.dict(exclude_unset=True)

        for k, v in values.items():
            setattr(instance, k, v)

        # all I do for now is create a ScrapeUpdate item, which contains a timestamp, and it is appended
        # to the self.scrape_updates list
        # as a transaction

        su = ScrapeUpdate(
            scrape_base_id=str(instance.uuid), scrape_type=self.model.__tablename__
        )
        self.session.add(su)

        # current_nupdate: int = getattr(instance, "nupdate", 0)
        # current_nupdate: int = instance.nupdate
        # logger.info(f"{current_nupdate=} \n\n{instance=}")

        # setattr(instance, "nupdate", current_nupdate + 1)

        # instance.updated_at = datetime.utcnow()

        # TODO: also implement for `create` method
        # TODO: why not use the crud?
        # TODO: turn into transaction? every time event is commited, create ScrapeUpdate record

        self.session.add(instance)
        try:
            await self.session.commit()
        except Exception as e:
            logger.warning(f"could not patch {model_id=}")
            raise

        await self.session.refresh(instance)

        return instance

    async def create(self, data: CreateType, **kwargs) -> ModelType:
        """Create a model instance.

        kwargs are used to pass extra attributes to model instantiation methods
        """
        # don't know how to fix this yet, createEvent converts to Event,
        # but mypy doesn't like this
        # logger.info(f"data.dict={pformat(data.dict())} \n\n{kwargs=}")

        instance: ModelType = self.model(**data.dict(), **kwargs)
        self.session.add(instance)

        # always add a scrapeUpdate item
        su = ScrapeUpdate(
            scrape_base_id=str(instance.uuid), scrape_type=self.model.__tablename__
        )
        self.session.add(su)

        # causes many crashes..
        try:
            await self.session.commit()
        except Exception as e:
            logger.warning(f"cannot create `{self.model.__tablename__}` item.")
            raise

        await self.session.refresh(instance)
        return instance

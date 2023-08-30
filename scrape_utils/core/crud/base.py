"""base.py.

Base CRUD class
"""
import importlib
import logging
from pprint import pformat
from typing import Generic, Optional, Type
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import delete, func, select
from sqlmodel import SQLModel

from ...models.main import UUIDModel
# from ...models.scrape.scrape_update import ScrapeUpdate
from ...types import CreateType, ModelType, PatchType
from .base_abc import BaseCRUDABC

# from sqlmodel.ext.asyncio.session import AsyncSession


logger = logging.getLogger(__name__)


class BaseCRUD(BaseCRUDABC, Generic[ModelType]):
    """BaseCRUD class that implements base functionality for CRUD operations of any SQLModel model."""

    # TODO: so do not create scrapeUpdates in this class

    # model: Optional[Type[ModelType]] = None

    # def __init__(self, session: AsyncSession, upsertKey: str) -> None:
    #     self.session: AsyncSession = session
    #     # logger.info(f"{dir(self.model)=}")
    #     # assert hasattr(
    #     #     model, upsertKey
    #     # ), f"{upsertKey=} not in {model=}. Use a different upsertKey"
    #     self.upsertKey: str = upsertKey
    #     self._cached_patch_model = self._get_patch_model()

    #     # logger.info(f"{self.model=} {type(self.model)=}")
    #     # if self.model is None:
    #     #     raise Exception(
    #     #         "please set Model first. Are you instantiating from a base class?"
    #     #     )

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "model"):
            raise Exception("Derived class must set the 'model' attribute")
        super().__init_subclass__(**kwargs)

    # TODO: make this work with class variable: `model`, set in events.crud
    # dynamically determine the PatchType
    @classmethod
    def _get_patch_model(cls) -> Type:
        model_name = cls.model.__name__
        module_name = cls.model.__module__
        patch_model_name = f"{model_name}Patch"
        patch_module = importlib.import_module(module_name)
        try:
            PatchModel = getattr(patch_module, patch_model_name)
        except AttributeError:
            logger.error(f"please implement `{patch_model_name}` for {module_name}")
            raise

        return PatchModel

    @property
    def PatchModel(self) -> Type:
        # if not hasattr(self, "_cached_patch_type"):
        #     self._cached_patch_model = self._get_patch_model()
        return self._cached_patch_model

    # TODO: try to cache the method
    @classmethod
    # def _id_attr_name(cls, model: Type[ModelType]) -> str:
    def _id_attr_name(cls, other_model: Optional[Type[ModelType]] = None) -> str:
        """Get `id` attribute name.

        for UUIDModels `id` is called `uuid`, otherwise `id`
        """
        model = other_model or cls.model

        assert isinstance(model, type), f"should pass a class"

        assert issubclass(model, SQLModel), f"{model} should be a subclass of SQLModel"

        # logger.info(f"{model=} {type(model)=}")

        # always use uuid attribute?
        # return "uuid"
        # TODO: try to always return the right id attribute name
        attr_name: str = model.__table__.primary_key.columns.items()[0][0]
        assert isinstance(attr_name, str), f"{attr_name=} {type(attr_name)=}"
        return attr_name

    @classmethod
    def _get_id_attr(
        cls, instance, other_model: Optional[Type[ModelType]] = None
    ) -> str:
        """Get `id` attribute value."""
        id_attr: str = cls._id_attr_name(other_model=other_model)

        return getattr(instance, id_attr)

    # TODO: moved to .scrape_item.py, since it uses ScrapeUpdate class. but other projects do not need this.
    # async def create(self, data: CreateType, **kwargs) -> ModelType:
    #     """Create a model instance.

    #     kwargs are used to pass extra attributes to model instantiation methods
    #     """
    #     # don't know how to fix this yet, createEvent converts to Event,
    #     # but mypy doesn't like this
    #     # logger.info(f"data.dict={pformat(data.dict())} \n\n{kwargs=}")

    #     instance: ModelType = self.model(**data.dict(), **kwargs)
    #     self.session.add(instance)

    #     # always add a scrapeUpdate item
    #     su = ScrapeUpdate(
    #         scrape_base_id=str(instance.uuid), scrape_type=self.model.__tablename__
    #     )
    #     self.session.add(su)

    #     # causes many crashes..
    #     try:
    #         await self.session.commit()
    #     except Exception as e:
    #         logger.warning(f"cannot create `{self.model.__tablename__}` item.")
    #         raise

    #     await self.session.refresh(instance)
    #     return instance

    async def create(self, data: CreateType, **kwargs) -> ModelType:
        """Create a model instance.

        kwargs are used to pass extra attributes to model instantiation methods
        """
        # don't know how to fix this yet, createEvent converts to Event,
        # but mypy doesn't like this
        # logger.info(f"data.dict={pformat(data.dict())} \n\n{kwargs=}")

        instance: ModelType = self.model(**data.dict(), **kwargs)
        self.session.add(instance)

        try:
            await self.session.commit()
        except Exception as e:
            logger.warning(f"cannot create `{self.model.__tablename__}` item.")
            raise

        await self.session.refresh(instance)
        return instance

    async def get(self, model_id: str | UUID) -> ModelType:
        """Get a model instance."""
        assert isinstance(model_id, (str, UUID)), f"{type(model_id)=}"
        # id_attr = self._id_attr_name()
        # logger.info(f"{model_id=}")
        # statement = select(self.model).where(self.model.uuid == model_id)
        statement = select(self.model).where(self._get_id_attr(self.model) == str(model_id))
        # statement = select(self.model).where(id_attr == model_id)
        results = await self.session.execute(statement=statement)
        # logger.info(f"{results=}")
        # logger.info(f"{dir(results)=}")
        # logger.info(f"{len(results.fetchall())=}")
        instance = results.scalar_one_or_none()
        if instance is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="The model hasn't been found!",
            )
        return instance

    async def upsert(self, data: CreateType, **kwargs) -> ModelType:
        """Create or patch a model instance."""
        # check if exists
        result = await self.session.execute(
            select([self.model]).where(
                getattr(self.model, self.upsertKey) == getattr(data, self.upsertKey)
            )
        )
        # logger.warning(f"{dir(result)=}")
        item_res = result.one_or_none()
        # assert isinstance(item, Event)
        # logger.info(f"{item_res=} \n{type(item_res)=}")

        # no, create it
        if item_res is None:
            instance: ModelType = await self.create(data, **kwargs)
            # logger.info(f"{dir(instance)=}")
            logger.info(
                f"created {instance.__tablename__} id={self._get_id_attr(instance)}. {self.upsertKey}={getattr(instance, self.upsertKey)}"
            )
            return instance

        # yes, patch it
        # else:
        item: ModelType = item_res[0]
        # logger.info(f"updating {item.uuid=}")
        logger.info(f"updating {item.__tablename__} id={self._get_id_attr(item)}")
        # typecast create to patch object
        # data_patch: PatchType = EventPatch(**data.dict())
        # data_patch: Type[self.PatchType] = self.PatchType(**data.dict())

        # TODO: enable again
        # logger.warning("DISABLE PATCH FOR NOW")
        data_patch = self.PatchModel(**data.dict())

        # TODO: deligate to the children class..
        # logger.info(f"data={pformat(item.dict())}")
        # logger.info("WILL PATCH")
        # return await self.patch(self._get_id_attr(item), data=data_patch, **kwargs)
        # logger.info(f"{self._id_attr_name()=} {getattr(item, self._id_attr_name())=}")
        # return await self.patch(
        #     getattr(data, self._id_attr_name()), data=data_patch, **kwargs
        # )
        return await self.patch(self._get_id_attr(item), data=data_patch, **kwargs)

    async def patch(self, model_id: str | UUID, data: PatchType, **kwargs) -> ModelType:
        """Patch a model instance."""
        instance: ModelType = await self.get(model_id=model_id)
        values = data.dict(exclude_unset=True)

        for k, v in values.items():
            setattr(instance, k, v)

        self.session.add(instance)
        await self.session.commit()

        logger.info(f"PATCHED {model_id}")
        return instance

    async def delete(self, model_id: str | UUID) -> bool:
        """Delete a model instance."""
        id_attr = self._id_attr_name()
        statement = delete(self.model).where(id_attr == model_id)

        await self.session.execute(statement=statement)
        await self.session.commit()

        return True

    async def nitem(self) -> Optional[int]:
        """Return the number of items for the model in the database."""
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar()

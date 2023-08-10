"""base.py.

Base CRUD class
"""
import importlib
import logging
from abc import ABC, abstractmethod
from pprint import pformat
from typing import Generic, List, Optional, Type
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...models.main import UUIDModel
from ...models.scrape.scrape_update import ScrapeUpdate
from ...types import CreateType, ModelType, PatchType

logger = logging.getLogger(__name__)


class BaseCRUDABC(ABC, Generic[ModelType]):
    """BaseCRUD ABC skeleton class."""

    model: Optional[Type[ModelType]] = None

    def __init__(self, session: AsyncSession, upsertKey: str) -> None:
        self.session: AsyncSession = session
        # logger.info(f"{dir(self.model)=}")
        # assert hasattr(
        #     model, upsertKey
        # ), f"{upsertKey=} not in {model=}. Use a different upsertKey"
        self.upsertKey: str = upsertKey
        self._cached_patch_model = self._get_patch_model()

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

    @abstractmethod
    async def create(self, data: CreateType) -> ModelType:
        pass

    @abstractmethod
    async def get(self, model_id: str | UUID) -> ModelType:
        pass

    @abstractmethod
    async def patch(self, model_id: str | UUID, data: PatchType) -> ModelType:
        pass

    @abstractmethod
    async def upsert(self, data: CreateType) -> ModelType:
        pass

    @abstractmethod
    async def delete(self, model_id: str | UUID) -> bool:
        pass


class BaseCRUD(BaseCRUDABC, Generic[ModelType]):
    """BaseCRUD class that implements base functionality for CRUD operations of any SQLModel mode."""

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

    # TODO: can be cached method
    @classmethod
    # def _id_attr_name(cls, model: Type[ModelType]) -> str:
    def _id_attr_name(cls, other_model: Optional[Type[ModelType]] = None) -> str:
        """Get `id` attribute name.

        for UUIDModels `id` is called `uuid`, otherwise `id`
        """
        model = other_model or cls.model

        assert isinstance(model, type), f"should pass a class"

        # logger.info(f"{model=} {type(model)=}")

        # return (
        #     getattr(model, "uuid")
        #     # if issubclass(model, UUIDModel)
        #     if isinstance(model, UUIDModel)
        #     else getattr(model, "id")
        # )

        return "uuid" if issubclass(model, UUIDModel) else "id"

    @classmethod
    def _get_id_attr(
        cls, instance, other_model: Optional[Type[ModelType]] = None
    ) -> str:
        """Get `id` attribute value."""
        id_attr: str = cls._id_attr_name(other_model=other_model)

        return getattr(instance, id_attr)

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
            scrape_base_id=instance.uuid, scrape_type=self.model.__tablename__
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

    async def get(self, model_id: str | UUID) -> ModelType:
        """Get a model instance."""
        assert isinstance(model_id, (str, UUID)), f"{type(model_id)=}"
        # id_attr = self._id_attr_name()
        # logger.info(f"{model_id=}")
        statement = select(self.model).where(self.model.uuid == model_id)
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


class CategoryItemCRUD(Generic[ModelType]):
    """Implements functionality for working with category items.

    Such as creating batches of items
    """

    model: Optional[Type[ModelType]] = None

    def __init__(self, session: AsyncSession, upsertKey: str) -> None:
        self.session: AsyncSession = session
        # logger.info(f"{dir(self.model)=}")
        # assert hasattr(
        #     model, upsertKey
        # ), f"{upsertKey=} not in {model=}. Use a different upsertKey"
        self.upsertKey: str = upsertKey
        self._cached_create_model = self._get_create_model()

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "model"):
            raise Exception("Derived class must set the 'model' attribute")
        super().__init_subclass__(**kwargs)

    @classmethod
    def _get_create_model(cls) -> Type:
        model_name = cls.model.__name__
        module_name = cls.model.__module__
        create_model_name = f"{model_name}Create"
        create_module = importlib.import_module(module_name)
        try:
            CreateModel = getattr(create_module, create_model_name)
        except AttributeError:
            logger.error(f"please implement `{create_model_name}` for {module_name}")
            raise

        return CreateModel

    @property
    def CreateModel(self) -> Type:
        # if not hasattr(self, "_cached_create_type"):
        #     self._cached_create_model = self._get_create_model()
        return self._cached_create_model

    async def get_create_batch(
        # self, data: List[TopicCreate], refresh=True
        self,
        data: List[ModelType],
        refresh=True,
    ) -> List[ModelType]:
        """Get or create a batch of category items."""
        # check if topic names exist in db
        # logger.info(f"create topic batch: {data=}")
        # logger.info(f"{dir(self.session)=}")

        # Get all existing items that match the list of names
        # query = select(self.model).where(self.model.name.in_([d.name for d in data]))
        # attr_col = self.model.__table__.c.name
        attr_col = getattr(self.model.__table__.c, self.upsertKey)
        # query = select(self.model).where(name_col.in_([d.name for d in data]))
        query = select(self.model).where(
            attr_col.in_([getattr(d, self.upsertKey) for d in data])
        )
        existing_instances = await self.session.execute(query)
        existing_instances = existing_instances.scalars().all()

        # Create new instances for items that don't exist
        existing_names = {i.name for i in existing_instances}
        new_instances = [
            self.model(**d.dict()) for d in data if d.name not in existing_names
        ]

        logger.info(
            f"creating {self.model.__table__}. {len(data)=} {len(existing_instances)=} {len(new_instances)=}"
        )

        # Bulk save the new instances to the database
        if new_instances:
            self.session.add_all(new_instances)

        await self.session.commit()

        # # Refresh all instances if requested
        # if refresh:
        #     for instance in existing_instances + new_instances:
        #         await self.session.refresh(instance)

        return existing_instances + new_instances

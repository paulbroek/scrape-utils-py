"""category_item.py.

CategoryItem CRUD class
"""
import importlib
import logging
from typing import Generic, List, Optional, Type

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...types import ModelType

logger = logging.getLogger(__name__)


class CategoryItemCRUD(Generic[ModelType]):
    """Implements functionality for working with category items.

    Such as creating batches of items
    """

    model: Optional[Type[ModelType]] = None

    def __init__(self, session: AsyncSession, upsertKey: str) -> None:
        self.session: AsyncSession = session
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
        self,
        data: List[ModelType],
        refresh=True,
    ) -> List[ModelType]:
        """Get or create a batch of category items."""
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


async def create_category_mappings(item: dict, categories: dict) -> dict:
    to_return = {}
    for cat, mapping in categories.items():
        if cat in item["item"]:
            logger.info(f"n{cat} in {item['type']}: {len(item['item'][cat])}")

            # create genres first in a batch
            to_return[cat] = await mapping["crud"].get_create_batch(
                [mapping["create_model"](name=n) for n in item["item"][cat]]
            )

    return to_return

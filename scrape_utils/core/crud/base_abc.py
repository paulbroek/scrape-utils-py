"""base_abc.py.

Base CRUD ABC class
"""
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Generic, Optional, Type
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

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

import logging
# from sys import modules
from typing import AsyncGenerator, Final

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future.engine import Engine
# from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

# from .. import settings

logger = logging.getLogger(__name__)


# uses the test string only if pytest was imported
# db_connection_str: Final[str] = (
#     settings.db_async_test_connection_str
#     if "pytest" in modules
#     else settings.db_async_connection_str
# )

# db_connection_str: Final[str] = settings.db_async_connection_str


poolSize: Final[int] = 40


def get_async_engine(settings):
    async_engine = create_async_engine(
        settings.db_async_connection_str,
        echo=False,
        future=True,
        pool_size=poolSize,
    )

    return async_engine


# engine = create_engine(settings.db_connection_str, echo=True)


async def init_db(settings):
    async with get_async_engine(settings).begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


# async def get_async_session() -> AsyncSession:
def get_async_session(settings) -> sessionmaker:
    async_session = sessionmaker(
        bind=get_async_engine(settings),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session
    # async with async_session() as session:
    #     yield session


async def yield_async_Session(settings) -> AsyncGenerator:
    async_session = get_async_session(settings)
    async with async_session() as session:
        yield session


def get_engine(settings, **kwargs) -> Engine:
    engine: Engine = create_engine(settings.db_connection_str, **kwargs)
    return engine


def get_session(settings, echo: bool = False) -> Session:
    engine: Engine = get_engine(settings, echo=echo)
    return Session(engine)

"""db.py.

PostgreSQL connection methods
"""
import logging
from typing import AsyncGenerator, Final

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from .settings import PG_POOL_SIZE_DEFAULT

logger = logging.getLogger(__name__)


def get_async_engine(async_connection_str: str, pool_size: int = PG_POOL_SIZE_DEFAULT):
    async_engine = create_async_engine(
        async_connection_str,
        echo=False,
        future=True,
        pool_size=pool_size,
    )

    return async_engine


async def init_db(async_connection_str: str):
    async with get_async_engine(async_connection_str).begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)


def get_async_session(
    async_connection_str: str, pool_size: int = PG_POOL_SIZE_DEFAULT
) -> sessionmaker:
    async_session = sessionmaker(
        bind=get_async_engine(async_connection_str, pool_size=pool_size),
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session
    # async with async_session() as session:
    #     yield session


async def yield_async_Session(async_connection_str: str) -> AsyncGenerator:
    async_session = get_async_session(async_connection_str)
    async with async_session() as session:
        yield session


def get_engine(connection_str: str, **kwargs) -> Engine:
    engine: Engine = create_engine(connection_str, **kwargs)
    return engine


def get_session(connection_str: str, echo: bool = False) -> Session:
    engine: Engine = get_engine(connection_str, echo=echo)
    return Session(engine)

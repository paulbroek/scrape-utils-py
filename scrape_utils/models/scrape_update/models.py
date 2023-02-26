import uuid as uuid_pkg
from datetime import datetime
from typing import Optional

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import generic_relationship
from sqlalchemy_utils import generic_relationship
from sqlmodel import Field, ForeignKey, Relationship

from ...models.main import UUIDModel
from ..base import Base as SM_Base

# sqlmodel and sqlmodel can be used together, as long as their metadatas are combined in alembic `env.py` file
Base = declarative_base()

# from ..scrape_base import ScrapeBase


# TODO: another solution can be to use pure SQLAlchemy model here
# TODO: model is disabled, because I cannot get it to work with SQLModel,
# maybe rewrite in SQLAlchemy
class ScrapeUpdateBase(SM_Base):
    # updated_at = Column(DateTime, default=func.now())
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # update_type: str = Field(nullable=False)
    # external uuid of object that was updated
    # ext_uuid: uuid_pkg.UUID = Field(nullable=False, index=True)
    # type = Column(String(50))


class ScrapeUpdate(Base):
    __tablename__ = "scrape_updates"
    # __table_args__ = {"info": {"schema": "my_schema"}}

    # id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)

    scrape_type = Column(String(255), nullable=False)

    created_at = Column(DateTime, server_default=func.now())  # current_timestamp()

    # scrape_base_id = Column(UUID(as_uuid=True), ForeignKey("scrape_base.uuid"))
    scrape_base_id = Column(UUID(as_uuid=True), nullable=False)
    # scrape_base_id = Column(UUID(as_uuid=True))
    # scrape_base_id = Column(UUID(as_uuid=True), ForeignKey("scrape_base.id"))
    # scrape_base_id: uuid_pkg.UUID = Field(foreign_key="scrape_base.id", nullable=False)
    # scrape_base: ScrapeBase = Relationship(back_populates="scrape_updates")
    scrape_base = generic_relationship(scrape_type, scrape_base_id)

    __mapper_args__ = {
        "polymorphic_on": "scrape_type",
        "polymorphic_identity": "scrape_updates",
        # "concrete": True,
    }


# class ScrapeUpdate(ScrapeUpdateBase, UUIDModel, table=True):
#     __tablename__ = "scrape_updates"

#     scrape_type: str = Field(nullable=False)
#     # scrape_base_id: uuid_pkg.UUID = Field(default=None, foreign_key="scrape_base.id")
#     scrape_base_id: uuid_pkg.UUID = Field(foreign_key="scrape_base.id", nullable=False)
#     # scrape_base: ScrapeBase = Relationship(back_populates="scrape_updates")
#     scrape_base = generic_relationship(scrape_type, scrape_base_id)
#     # scrape_base = Relationship(back_populates="updates")

#     __mapper_args__ = {
#         "polymorphic_on": "scrape_type",
#         "polymorphic_identity": "scrape_updates",
#         # "concrete": True,
#     }

#     # class Config:
#     #     orm_mode = True
#     #     arbitrary_types_allowed = True


class ScrapeUpdateRead(ScrapeUpdateBase, UUIDModel):
    pass


class ScrapeUpdateCreate(ScrapeUpdateBase):
    pass


# NO patch model, eventUpdate are always unique and cannot be updated

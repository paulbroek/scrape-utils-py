import uuid as uuid_pkg

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import generic_relationship  # type: ignore[import]

# sqlmodel and sqlmodel can be used together, as long as their metadatas are combined in alembic `env.py` file
Base = declarative_base()

# TODO: disable for now, first fix inheriting from Base without adding table to same shared library base.metadata
# class ScrapeUpdateBase(SM_Base):
#     created_at: datetime = Field(
#         default_factory=datetime.utcnow, index=True, nullable=False
#     )


class ScrapeUpdate(Base):
    __tablename__ = "scrape_updates"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)

    scrape_type = Column(String(255), nullable=False)

    created_at = Column(DateTime, server_default=func.now())  # current_timestamp()

    # scrape_base_id = Column(UUID(as_uuid=True), nullable=False)
    # to support both UUID and string id types
    scrape_base_id = Column(String, nullable=False)
    scrape_base = generic_relationship(scrape_type, scrape_base_id)

    __mapper_args__ = {
        "polymorphic_on": "scrape_type",
        "polymorphic_identity": "scrape_updates",
        # "concrete": True,
    }

    __table_args__ = (Index("ix_created_at", "created_at"),)


# class ScrapeUpdateRead(ScrapeUpdateBase, UUIDModel):
#     pass


# class ScrapeUpdateCreate(ScrapeUpdateBase):
#     pass


# NO patch model, eventUpdate are always unique and cannot be updated

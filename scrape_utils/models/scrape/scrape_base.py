from datetime import datetime
from typing import List

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import ConcreteBase
from sqlmodel import Field, Relationship, SQLModel

# from ...models import Base
from ...models import BaseScrapeUtility
from ...models.scrape.scrape_update import ScrapeUpdate

# TODO: trying to rewrite into mixin, so that table can be reused in many projects
# without depending on same Base metadata
# class ScrapeBaseMixin(BaseScrapeUtility):
# class ScrapeBase(BaseScrapeUtility):
#     """ScrapeBase model."""

#     # __abstract__ = True
#     __tablename__ = "scrape_base"

#     # scrape_type: str = Field(nullable=False)
#     # scrape_type: Optional[str] = Field(nullable=True)

#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

#     updates: List[ScrapeUpdate] = Relationship(back_populates="scrape_base")

#     __mapper_args__ = {
#         "polymorphic_identity": "scrape_base",
#         # "polymorphic_identity": None,
#         # "polymorphic_identity": "regular",
#         # "polymorphic_on": "scrape_type",
#         "concrete": True,
#     }


# class ScrapeBase(ConcreteBase, Base):
# class ScrapeBase(Base):
# class ScrapeBaseMixin(BaseScrapeUtility):
class ScrapeBase(BaseScrapeUtility):
    """ScrapeBase model."""

    # __abstract__ = True
    __tablename__ = "scrape_base"

    # scrape_type: str = Field(nullable=False)
    # scrape_type: Optional[str] = Field(nullable=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    updates: List[ScrapeUpdate] = Relationship(back_populates="scrape_base")

    __mapper_args__ = {
        "polymorphic_identity": "scrape_base",
        # "polymorphic_identity": None,
        # "polymorphic_identity": "regular",
        # "polymorphic_on": "scrape_type",
        "concrete": True,
    }


# class Scrapable(ScrapeBase):
#     __abstract__ = True

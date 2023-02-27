from datetime import datetime
from typing import List

from sqlalchemy.ext.declarative import ConcreteBase
from sqlmodel import Field, Relationship

from ...models import Base
from ...models.scrape.scrape_update import ScrapeUpdate


# class ScrapeBase(ConcreteBase, Base):
class ScrapeBase(Base):
    """ScrapeBase Meetup model."""

    __abstract__ = True
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

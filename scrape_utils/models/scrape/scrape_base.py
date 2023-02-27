from datetime import datetime
from typing import List, Optional

from scrape_utils.models import Base
from scrape_utils.models.scrape_update import ScrapeUpdate
from sqlalchemy.ext.declarative import ConcreteBase, declarative_base
from sqlmodel import Field, ForeignKey, Relationship


# class ScrapeBase(ConcreteBase, Base):
class ScrapeBase(Base):
    """ScrapeBase Meetup model."""

    __abstract__ = True
    __tablename__ = "scrape_base"

    # no longer neccesary, scrape_update contains this information
    # last_scraped: datetime = Field(nullable=False)
    # nupdate: int = Field(default_factory=set_nupdate_to_zero)
    # TODO: or add a ScrapeUpdate model?
    # nupdate: int = Field(default=0)
    # scrape_type: str = Field(nullable=False)
    # scrape_type: Optional[str] = Field(nullable=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # updates: List["ScrapeUpdate"] = Relationship(back_populates="scrape_base")
    updates: List[ScrapeUpdate] = Relationship(back_populates="scrape_base")
    # update: "ScrapeUpdate" = Relationship(back_populates="scrape_base")
    # relationship("ScrapeUpdate", back_populates="scrape_base")

    # TODO: add indices for `updated_at` and `url`

    # updates = relationship(
    #     "ScrapeUpdate", back_populates="scrape_base", cascade="all, delete-orphan"
    # )

    __mapper_args__ = {
        "polymorphic_identity": "scrape_base",
        # "polymorphic_identity": None,
        # "polymorphic_identity": "regular",
        # "polymorphic_on": "scrape_type",
        "concrete": True,
    }


# class Scrapable(ScrapeBase):
#     __abstract__ = True

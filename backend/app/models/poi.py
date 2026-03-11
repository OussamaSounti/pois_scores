"""SQLAlchemy model for production.pois (main POI table)."""

from sqlalchemy import BigInteger, Double, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Poi(Base):
    """production.pois — main POI table for score API. Read-only."""

    __tablename__ = "pois"
    __table_args__ = {"schema": "production"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    osm_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Unnamed")
    fclass: Mapped[str] = mapped_column(Text, nullable=False)
    super_category: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    # geom exists in DB for spatial indexes; we use raw SQL for PostGIS queries

"""SQLAlchemy ORM model for ``active.production_pois_current``.

Mirrors the external POI contract exactly: ``osm_id, name, fclass,
super_category, lat, lon, geom``. Read-only from this codebase's perspective.
"""

from sqlalchemy import Double, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Poi(Base):
    """``active.production_pois_current`` — flat current snapshot.

    The upstream pipeline guarantees one canonical row per physical POI; no
    ``is_canonical`` filter is needed for this table (only for history).
    """

    __tablename__ = "production_pois_current"
    __table_args__ = {"schema": "active"}

    osm_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Unnamed")
    fclass: Mapped[str] = mapped_column(Text, nullable=False)
    super_category: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lon: Mapped[float] = mapped_column(Double, nullable=False)
    # geom exists in DB for spatial indexes; raw SQL is used for PostGIS queries.

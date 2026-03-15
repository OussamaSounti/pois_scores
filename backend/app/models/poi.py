"""SQLAlchemy model for production.pois_current (main POI table)."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Double, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Poi(Base):
    """production.pois_current — main POI table for score API. Read-only."""

    __tablename__ = "pois_current"
    __table_args__ = {"schema": "production"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    osm_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Unnamed")
    fclass: Mapped[str] = mapped_column(Text, nullable=False)
    super_category: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    source_snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # geom exists in DB for spatial indexes; we use raw SQL for PostGIS queries

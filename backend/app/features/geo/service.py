"""GeoJSON business logic — delegates data access to :class:`GeoReferenceRepository`."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.geo import GeoReferenceRepository


def get_land_feature_collection(session: Session) -> dict[str, Any]:
    return GeoReferenceRepository(session).get_land_feature_collection()


def get_coastline_feature_collection(session: Session) -> dict[str, Any]:
    return GeoReferenceRepository(session).get_coastline_feature_collection()

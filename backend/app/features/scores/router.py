"""Single-location and batch POI score endpoints."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.scores.schemas import (
    BatchScoresRequest,
    BatchScoresResponse,
    LocationIn,
    LocationOut,
    ScoreResponse,
    ScoresPayload,
)
from app.features.scores.service import compute_scores, compute_scores_at_date

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scores", tags=["scores"])


def _compute(db: Session, lat: float, lon: float, as_of: date | None) -> dict:
    """Dispatch to temporal or current scoring based on whether as_of is provided."""
    if as_of is not None:
        return compute_scores_at_date(db, lat, lon, as_of)
    return compute_scores(db, lat, lon)


@router.get("", response_model=ScoreResponse)
def get_score(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    as_of: date | None = Query(
        default=None,
        description=(
            "Optional date (YYYY-MM-DD) to score the location using the historical "
            "POI snapshot at that date. When omitted, the current POI snapshot is used."
        ),
    ),
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Get POI scores for a single location (query params).

    Pass ``as_of=YYYY-MM-DD`` for historical scoring.
    """
    try:
        payload = _compute(db, lat, lon, as_of)
    except Exception as e:
        logger.exception("Score computation failed for lat=%s lon=%s as_of=%s", lat, lon, as_of)
        raise HTTPException(
            status_code=500,
            detail=f"Score computation failed: {e!s}",
        ) from e
    return ScoreResponse(
        location=LocationOut(lat=lat, lon=lon),
        scores=ScoresPayload(**payload),
    )


@router.post("", response_model=ScoreResponse)
def post_score(
    body: LocationIn,
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Get POI scores for a single location (JSON body). Include as_of for historical scoring."""
    try:
        payload = _compute(db, body.lat, body.lon, body.as_of)
    except Exception as e:
        logger.exception(
            "Score computation failed for lat=%s lon=%s as_of=%s", body.lat, body.lon, body.as_of
        )
        raise HTTPException(
            status_code=500,
            detail=f"Score computation failed: {e!s}",
        ) from e
    return ScoreResponse(
        location=LocationOut(lat=body.lat, lon=body.lon),
        scores=ScoresPayload(**payload),
    )


@router.post("/batch", response_model=BatchScoresResponse)
def post_score_batch(
    body: BatchScoresRequest,
    db: Session = Depends(get_db),
) -> BatchScoresResponse:
    """Get POI scores for multiple locations (cap defined by core.constants.BATCH_MAX_LOCATIONS).

    Each item may include as_of for per-location historical scoring.
    """
    results = []
    for loc in body.locations:
        try:
            payload = _compute(db, loc.lat, loc.lon, loc.as_of)
        except Exception as e:
            logger.exception(
                "Score computation failed for lat=%s lon=%s as_of=%s", loc.lat, loc.lon, loc.as_of
            )
            raise HTTPException(
                status_code=500,
                detail=f"Score computation failed: {e!s}",
            ) from e
        results.append(
            ScoreResponse(
                location=LocationOut(lat=loc.lat, lon=loc.lon),
                scores=ScoresPayload(**payload),
            )
        )
    return BatchScoresResponse(results=results)

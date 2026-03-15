"""Single-location and batch POI score endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.scores import (
    BatchScoresRequest,
    BatchScoresResponse,
    LocationIn,
    LocationOut,
    ScoreResponse,
    ScoresPayload,
)
from app.services.spatial import compute_scores

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("", response_model=ScoreResponse)
def get_score(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Get POI scores for a single location (query params)."""
    try:
        payload = compute_scores(db, lat, lon)
    except Exception as e:
        logger.exception("Score computation failed for lat=%s lon=%s", lat, lon)
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
    """Get POI scores for a single location (JSON body)."""
    try:
        payload = compute_scores(db, body.lat, body.lon)
    except Exception as e:
        logger.exception("Score computation failed for lat=%s lon=%s", body.lat, body.lon)
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
    """Get POI scores for multiple locations. Results in same order as input (max 500)."""
    results = []
    for loc in body.locations:
        try:
            payload = compute_scores(db, loc.lat, loc.lon)
        except Exception as e:
            logger.exception(
                "Score computation failed for lat=%s lon=%s", loc.lat, loc.lon
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

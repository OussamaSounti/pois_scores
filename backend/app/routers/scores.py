"""Single-location and batch POI score endpoints."""

from fastapi import APIRouter, Depends, Query
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

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("", response_model=ScoreResponse)
def get_score(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
) -> ScoreResponse:
    """Get POI scores for a single location (query params)."""
    payload = compute_scores(db, lat, lon)
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
    payload = compute_scores(db, body.lat, body.lon)
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
        payload = compute_scores(db, loc.lat, loc.lon)
        results.append(
            ScoreResponse(
                location=LocationOut(lat=loc.lat, lon=loc.lon),
                scores=ScoresPayload(**payload),
            )
        )
    return BatchScoresResponse(results=results)

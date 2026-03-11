"""Single-location POI score endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.scores import LocationIn, LocationOut, ScoreResponse, ScoresPayload
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

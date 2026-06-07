"""Morocco Spatial Dashboard — FastAPI application entrypoint.

This file does only routing wiring. Each feature owns its router, schemas
and service in ``app.features.<feature>``; cross-cutting code (settings,
DB session, metrics, constants, generic spatial primitives) lives in
``app.core``.
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.metrics import get_metrics
from app.features.geo.router import router as geo_router
from app.features.pois.router import router as pois_router
from app.features.properties.router import router as properties_router
from app.features.scores.router import router as scores_router

app = FastAPI(
    title="Morocco Spatial Dashboard API",
    description="POI-based spatial scores for locations in Morocco (single and batch).",
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scores_router, prefix="/api/v1")
app.include_router(pois_router, prefix="/api/v1")
app.include_router(properties_router, prefix="/api/v1")
app.include_router(geo_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness: always 200 if the process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: 200 if DB is reachable, 503 otherwise."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unreachable")


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)

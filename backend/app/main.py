"""Morocco Spatial Dashboard — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.config import get_settings
from app.metrics import get_metrics
from app.routers import health, pois, scores

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

app.include_router(health.router)
app.include_router(scores.router, prefix="/api/v1")
app.include_router(pois.router, prefix="/api/v1")


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)

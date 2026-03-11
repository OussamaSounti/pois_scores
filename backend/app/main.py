"""Morocco Spatial Dashboard — FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, scores

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

"""Application settings from environment.

Holds environment- and deployment-specific values: database DSN, log level,
CORS origins, pipeline version label, and Overpass / OSM ingest knobs used
by ``scripts/ingest/load_osm_*.py``.

Domain constants (radii, accessibility types, score-feature column names,
POI source enums) live in ``app.core.constants`` and are not configurable.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed environment settings loaded from process env and ``.env`` files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),  # backend/.env or project root .env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql://poi_user:poi_password@localhost:5432/poi_db"
    log_level: str = "info"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Fully-qualified source transactions table for dashboard joins and property sync.
    # Example: analytics.transactions. Empty = no join (slim properties only).
    transactions_table: str = ""

    # Version label written to production.property_features.pipeline_version.
    pipeline_version: str = "1.0"

    # Connection pool tuning for batch pipeline workloads.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    pipeline_workers: int = 4

    # Overpass / OSM ingest. Used by scripts/ingest/load_osm_*.py.
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    overpass_user_agent: str = "pois_scores_v2/1.0"
    overpass_query_timeout_s: int = 300
    overpass_http_timeout_s: int = 330
    osm_morocco_relation_id: int = 3630439
    osm_morocco_bbox: str = "27,-18,37,0"  # south, west, north, east

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins parsed from the comma-separated env value."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    """Return application settings (from env and .env files)."""
    return Settings()

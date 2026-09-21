"""Serve pipeline flows to local Prefect for UI testing.

Start a dedicated server first (separate terminal)::

    prefect server start

Then in this terminal::

    $env:PREFECT_API_URL = "http://127.0.0.1:4200/api"
    $env:DATABASE_URL = "postgresql://poi_user:poi_password@localhost:5432/poi_db"
    python serve_prefect_flows.py

Open http://127.0.0.1:4200 — trigger runs from Deployments (manual is best for chunk tests).
"""
from prefect import serve

from app.features.feature_pipeline.flow import (
    historical_backfill_flow,
    weekly_recompute_flow,
)

if __name__ == "__main__":
    serve(
        weekly_recompute_flow.to_deployment(
            name="weekly-new-transactions",
            # cron="0 2 * * 1",  # prod: Monday 02:00 after transaction ingest
            tags=["weekly", "manual"],
        ),
        historical_backfill_flow.to_deployment(
            name="historical-backfill",
            cron="*/5 * * * *",
            tags=["historical"],
        ),
    )
"""Shared upsert + pending-detection helpers for both pipeline flows.

Keeps SQL for ``production.property_features`` in one place so the two flow
modules only deal with their selection criteria.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import PROPERTY_FEATURE_COLUMNS

logger = logging.getLogger(__name__)


def get_current_poi_ts(session: Session) -> datetime:
    """Return the latest external POI refresh timestamp.

    Source: ``active.audit_pipeline_runs.max(run_timestamp)``. Falls back to
    ``now()`` (UTC) when the audit table has no rows.
    """
    row = session.execute(
        text("SELECT max(run_timestamp) FROM active.audit_pipeline_runs")
    ).scalar()
    if row is not None:
        return row if row.tzinfo else row.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def upsert_feature_rows(session: Session, rows: list[dict[str, Any]]) -> None:
    """Insert or update a batch of ``production.property_features`` rows.

    ``by_category`` and ``nearest_km`` are JSON-encoded on the way in.
    Commits on completion.
    """
    if not rows:
        return
    cols = list(PROPERTY_FEATURE_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "property_id")
    sql = text(
        f"""
        INSERT INTO production.property_features ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT (property_id) DO UPDATE SET {updates}
        """
    )
    for row in rows:
        payload = {c: row.get(c) for c in cols}
        payload["by_category"] = json.dumps(row["by_category"])
        payload["nearest_km"] = json.dumps(row["nearest_km"])
        session.execute(sql, payload)
    session.commit()

"""Load a transaction Parquet into staging.transactions and sync slim production.properties.

Dev workflow mirrors production: rich data stays in the source transactions table;
only coordinates and transaction_date are copied into production.properties for the
feature pipeline.

Usage:
  python scripts/ingest/load_properties_from_parquet.py --parquet input/casablanca_transactions_sample.parquet

Set TRANSACTIONS_TABLE=staging.transactions in .env so the Properties dashboard can
join attributes from the same source table.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import pandas as pd  # noqa: E402
import psycopg2  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.tables import T_PROPERTIES, T_TRANSACTIONS_DEV  # noqa: E402

# Columns stored in staging.transactions (dashboard attrs + coords). Must stay aligned
# with _TRANSACTION_ATTR_COLUMNS in backend/app/repositories/property.py.
TRANSACTION_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "asset_latitude",
    "asset_longitude",
    "transaction_date",
    "asset_price",
    "asset_surface",
    "asset_psqm",
    "asset_type",
    "district_uid",
    "district_name",
    "neighbourhood_uid",
    "neighbour_name",
    "iris_uid",
    "iris_code",
    "ilot_uid",
    "ilot_objectid",
)


def _is_nan(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _to_float(value: Any) -> float | None:
    if _is_nan(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _to_int(value: Any) -> int | None:
    if _is_nan(value):
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return int(value)
    except Exception:
        return None


def _to_text(value: Any) -> str | None:
    if _is_nan(value):
        return None
    text = str(value).strip()
    return text or None


def _to_date(value: Any) -> date | None:
    if _is_nan(value):
        return None
    try:
        ts = pd.to_datetime(value, utc=False)
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def ensure_schemas(conn: psycopg2.extensions.connection) -> None:
    """Create staging.transactions and slim production.properties if missing."""
    tx_cols = ",\n        ".join(
        f"{col} { _column_type(col) }" for col in TRANSACTION_COLUMNS
    )
    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE SCHEMA IF NOT EXISTS production;

    CREATE TABLE IF NOT EXISTS {T_TRANSACTIONS_DEV} (
        {tx_cols}
    );

    CREATE TABLE IF NOT EXISTS {T_PROPERTIES} (
        transaction_id bigint PRIMARY KEY,
        latitude double precision NOT NULL,
        longitude double precision NOT NULL,
        transaction_date date
    );

    CREATE INDEX IF NOT EXISTS idx_properties_transaction_date
        ON {T_PROPERTIES} (transaction_date);
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _column_type(col: str) -> str:
    if col == "transaction_id":
        return "bigint PRIMARY KEY"
    if col in ("asset_latitude", "asset_longitude", "asset_price", "asset_surface", "asset_psqm"):
        return "double precision"
    if col == "transaction_date":
        return "date"
    return "text"


def _record_to_row(record: dict[str, Any]) -> tuple[Any, ...] | None:
    tx_id = _to_int(record.get("transaction_id"))
    lat = _to_float(record.get("asset_latitude"))
    lon = _to_float(record.get("asset_longitude"))
    if tx_id is None or lat is None or lon is None:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    return tuple(
        tx_id if col == "transaction_id" else _field_value(record, col)
        for col in TRANSACTION_COLUMNS
    )


def _field_value(record: dict[str, Any], col: str) -> Any:
    if col in ("asset_latitude", "asset_longitude", "asset_price", "asset_surface", "asset_psqm"):
        return _to_float(record.get(col))
    if col == "transaction_date":
        return _to_date(record.get(col))
    if col.endswith("_uid") or col.endswith("_name") or col.endswith("_code") or col.endswith("_objectid") or col == "asset_type":
        return _to_text(record.get(col))
    return record.get(col)


def upsert_transactions(
    conn: psycopg2.extensions.connection, rows: list[tuple[Any, ...]], chunk_size: int
) -> int:
    """Bulk-upsert rows into staging.transactions."""
    cols = ", ".join(TRANSACTION_COLUMNS)
    updates = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in TRANSACTION_COLUMNS if col != "transaction_id"
    )
    sql = f"""
    INSERT INTO {T_TRANSACTIONS_DEV} ({cols})
    VALUES %s
    ON CONFLICT (transaction_id) DO UPDATE SET {updates}
    """
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            execute_values(cur, sql, chunk, page_size=chunk_size)
            total += len(chunk)
    conn.commit()
    return total


def sync_slim_properties(
    conn: psycopg2.extensions.connection, source_table: str = T_TRANSACTIONS_DEV
) -> int:
    """Copy coords + transaction_date from the transactions table into production.properties."""
    sql = f"""
    INSERT INTO {T_PROPERTIES} (transaction_id, latitude, longitude, transaction_date)
    SELECT
        transaction_id,
        asset_latitude,
        asset_longitude,
        transaction_date
    FROM {source_table}
    WHERE asset_latitude IS NOT NULL
      AND asset_longitude IS NOT NULL
      AND asset_latitude BETWEEN -90 AND 90
      AND asset_longitude BETWEEN -180 AND 180
    ON CONFLICT (transaction_id) DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        transaction_date = EXCLUDED.transaction_date
    RETURNING transaction_id
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        synced = len(cur.fetchall())
    conn.commit()
    return synced


def load_parquet(parquet_path: Path, chunk_size: int) -> tuple[int, int, int]:
    """Load parquet into staging.transactions and sync slim production.properties.

    Returns (loaded, skipped, synced).
    """
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    try:
        ensure_schemas(conn)

        df = pd.read_parquet(parquet_path)
        missing = [
            c for c in ("transaction_id", "asset_latitude", "asset_longitude") if c not in df.columns
        ]
        if missing:
            raise ValueError(
                "Parquet is missing required columns for properties ingestion: "
                + ", ".join(missing)
            )

        rows: list[tuple[Any, ...]] = []
        skipped = 0
        for rec in df.to_dict(orient="records"):
            row = _record_to_row(rec)
            if row is None:
                skipped += 1
                continue
            rows.append(row)

        loaded = upsert_transactions(conn, rows, chunk_size=chunk_size) if rows else 0
        synced = sync_slim_properties(conn)
        return loaded, skipped, synced
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the parquet ingest script."""
    parser = argparse.ArgumentParser(
        description="Ingest a transaction Parquet into staging.transactions and sync slim properties."
    )
    parser.add_argument("--parquet", required=True, help="Path to transaction parquet file.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Rows per database batch (default: 1000).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint: load parquet into staging.transactions and sync production.properties."""
    args = parse_args()
    parquet_path = Path(args.parquet).expanduser().resolve()
    if not parquet_path.exists():
        print(f"Parquet file not found: {parquet_path}", file=sys.stderr)
        return 1

    try:
        loaded, skipped, synced = load_parquet(parquet_path, chunk_size=args.chunk_size)
        print(f"Loaded/updated transactions: {loaded}")
        print(f"Synced pipeline properties: {synced}")
        print(f"Skipped rows (invalid/missing coords or id): {skipped}")
        return 0
    except Exception as exc:
        print(f"Parquet load failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

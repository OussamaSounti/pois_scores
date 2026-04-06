"""Expand production.properties for transaction columns and upsert rows from a Parquet file.

Usage:
  python scripts/load_properties_from_parquet.py --parquet ../input/casablanca_transactions_sample.parquet
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

# Ensure app package is importable when run as python scripts/load_properties_from_parquet.py
_app_root = Path(__file__).resolve().parent.parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from app.config import get_settings

try:
    from shapely import wkb as shapely_wkb
except Exception:  # pragma: no cover - optional dependency
    shapely_wkb = None


CORE_COLUMNS = {"id", "latitude", "longitude", "metadata"}
EXPECTED_COLUMNS = [
    "db_row_id",
    "transaction_id",
    "transaction_date",
    "transaction_year",
    "transaction_month",
    "transaction_quarter",
    "asset_price",
    "asset_surface",
    "asset_psqm",
    "asset_rooms",
    "asset_floor",
    "asset_type",
    "asset_geometry",
    "asset_latitude",
    "asset_longitude",
    "asset_hashed_title",
    "land_hashed_title",
    "land_geometry",
    "ilot_uid",
    "ilot_objectid",
    "ilot_geometry",
    "iris_uid",
    "iris_code",
    "iris_geometry",
    "neighbourhood_uid",
    "neighbour_name",
    "neighbourhood_geometry",
    "district_uid",
    "district_name",
    "district_geometry",
]


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


def _to_iso_datetime(value: Any) -> str | None:
    if _is_nan(value):
        return None
    try:
        ts = pd.to_datetime(value, utc=False)
        if pd.isna(ts):
            return None
        return ts.isoformat()
    except Exception:
        return None


def _bytes_to_wkt(blob: bytes | memoryview) -> str | None:
    if shapely_wkb is None:
        return None
    try:
        geom = shapely_wkb.loads(bytes(blob))
        return geom.wkt if geom else None
    except Exception:
        return None


def _to_wkt(value: Any) -> str | None:
    if _is_nan(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _bytes_to_wkt(value)
    if hasattr(value, "wkt"):
        try:
            return str(value.wkt)
        except Exception:
            return None
    return None


def ensure_target_schema(conn: psycopg2.extensions.connection) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS production;
    CREATE EXTENSION IF NOT EXISTS postgis;

    CREATE TABLE IF NOT EXISTS production.properties (
        id bigint PRIMARY KEY,
        latitude double precision NOT NULL,
        longitude double precision NOT NULL,
        metadata jsonb
    );

    ALTER TABLE production.properties
        ADD COLUMN IF NOT EXISTS db_row_id bigint,
        ADD COLUMN IF NOT EXISTS transaction_id bigint,
        ADD COLUMN IF NOT EXISTS transaction_date timestamp,
        ADD COLUMN IF NOT EXISTS transaction_year integer,
        ADD COLUMN IF NOT EXISTS transaction_month integer,
        ADD COLUMN IF NOT EXISTS transaction_quarter text,
        ADD COLUMN IF NOT EXISTS asset_price double precision,
        ADD COLUMN IF NOT EXISTS asset_surface double precision,
        ADD COLUMN IF NOT EXISTS asset_psqm double precision,
        ADD COLUMN IF NOT EXISTS asset_rooms double precision,
        ADD COLUMN IF NOT EXISTS asset_floor text,
        ADD COLUMN IF NOT EXISTS asset_type text,
        ADD COLUMN IF NOT EXISTS asset_geometry geometry(Point, 4326),
        ADD COLUMN IF NOT EXISTS asset_latitude double precision,
        ADD COLUMN IF NOT EXISTS asset_longitude double precision,
        ADD COLUMN IF NOT EXISTS asset_hashed_title text,
        ADD COLUMN IF NOT EXISTS land_hashed_title text,
        ADD COLUMN IF NOT EXISTS land_geometry geometry(Geometry, 4326),
        ADD COLUMN IF NOT EXISTS ilot_uid text,
        ADD COLUMN IF NOT EXISTS ilot_objectid text,
        ADD COLUMN IF NOT EXISTS ilot_geometry geometry(Geometry, 4326),
        ADD COLUMN IF NOT EXISTS iris_uid text,
        ADD COLUMN IF NOT EXISTS iris_code text,
        ADD COLUMN IF NOT EXISTS iris_geometry geometry(Geometry, 4326),
        ADD COLUMN IF NOT EXISTS neighbourhood_uid text,
        ADD COLUMN IF NOT EXISTS neighbour_name text,
        ADD COLUMN IF NOT EXISTS neighbourhood_geometry geometry(Geometry, 4326),
        ADD COLUMN IF NOT EXISTS district_uid text,
        ADD COLUMN IF NOT EXISTS district_name text,
        ADD COLUMN IF NOT EXISTS district_geometry geometry(Geometry, 4326);

    CREATE INDEX IF NOT EXISTS idx_properties_transaction_id
        ON production.properties(transaction_id);

    CREATE INDEX IF NOT EXISTS idx_properties_transaction_date
        ON production.properties(transaction_date);
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _build_metadata(record: dict[str, Any]) -> str:
    extras = {
        k: v
        for k, v in record.items()
        if k not in CORE_COLUMNS and k not in EXPECTED_COLUMNS and not _is_nan(v)
    }
    return json.dumps(extras) if extras else "{}"


def _record_to_row(record: dict[str, Any]) -> tuple[Any, ...] | None:
    tx_id = _to_int(record.get("transaction_id"))
    if tx_id is None:
        return None

    lat = _to_float(record.get("asset_latitude"))
    lon = _to_float(record.get("asset_longitude"))
    if lat is None or lon is None:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    asset_geometry_wkt = _to_wkt(record.get("asset_geometry"))
    if asset_geometry_wkt is None:
        asset_geometry_wkt = f"POINT({lon} {lat})"

    return (
        tx_id,
        lat,
        lon,
        _build_metadata(record),
        _to_int(record.get("db_row_id")),
        tx_id,
        _to_iso_datetime(record.get("transaction_date")),
        _to_int(record.get("transaction_year")),
        _to_int(record.get("transaction_month")),
        _to_text(record.get("transaction_quarter")),
        _to_float(record.get("asset_price")),
        _to_float(record.get("asset_surface")),
        _to_float(record.get("asset_psqm")),
        _to_float(record.get("asset_rooms")),
        _to_text(record.get("asset_floor")),
        _to_text(record.get("asset_type")),
        asset_geometry_wkt,
        lat,
        lon,
        _to_text(record.get("asset_hashed_title")),
        _to_text(record.get("land_hashed_title")),
        _to_wkt(record.get("land_geometry")),
        _to_text(record.get("ilot_uid")),
        _to_text(record.get("ilot_objectid")),
        _to_wkt(record.get("ilot_geometry")),
        _to_text(record.get("iris_uid")),
        _to_text(record.get("iris_code")),
        _to_wkt(record.get("iris_geometry")),
        _to_text(record.get("neighbourhood_uid")),
        _to_text(record.get("neighbour_name")),
        _to_wkt(record.get("neighbourhood_geometry")),
        _to_text(record.get("district_uid")),
        _to_text(record.get("district_name")),
        _to_wkt(record.get("district_geometry")),
    )


def upsert_rows(
    conn: psycopg2.extensions.connection, rows: list[tuple[Any, ...]], chunk_size: int
) -> int:
    sql = """
    INSERT INTO production.properties (
        id,
        latitude,
        longitude,
        metadata,
        db_row_id,
        transaction_id,
        transaction_date,
        transaction_year,
        transaction_month,
        transaction_quarter,
        asset_price,
        asset_surface,
        asset_psqm,
        asset_rooms,
        asset_floor,
        asset_type,
        asset_geometry,
        asset_latitude,
        asset_longitude,
        asset_hashed_title,
        land_hashed_title,
        land_geometry,
        ilot_uid,
        ilot_objectid,
        ilot_geometry,
        iris_uid,
        iris_code,
        iris_geometry,
        neighbourhood_uid,
        neighbour_name,
        neighbourhood_geometry,
        district_uid,
        district_name,
        district_geometry
    )
    VALUES %s
    ON CONFLICT (id) DO UPDATE SET
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        metadata = EXCLUDED.metadata,
        db_row_id = EXCLUDED.db_row_id,
        transaction_id = EXCLUDED.transaction_id,
        transaction_date = EXCLUDED.transaction_date,
        transaction_year = EXCLUDED.transaction_year,
        transaction_month = EXCLUDED.transaction_month,
        transaction_quarter = EXCLUDED.transaction_quarter,
        asset_price = EXCLUDED.asset_price,
        asset_surface = EXCLUDED.asset_surface,
        asset_psqm = EXCLUDED.asset_psqm,
        asset_rooms = EXCLUDED.asset_rooms,
        asset_floor = EXCLUDED.asset_floor,
        asset_type = EXCLUDED.asset_type,
        asset_geometry = EXCLUDED.asset_geometry,
        asset_latitude = EXCLUDED.asset_latitude,
        asset_longitude = EXCLUDED.asset_longitude,
        asset_hashed_title = EXCLUDED.asset_hashed_title,
        land_hashed_title = EXCLUDED.land_hashed_title,
        land_geometry = EXCLUDED.land_geometry,
        ilot_uid = EXCLUDED.ilot_uid,
        ilot_objectid = EXCLUDED.ilot_objectid,
        ilot_geometry = EXCLUDED.ilot_geometry,
        iris_uid = EXCLUDED.iris_uid,
        iris_code = EXCLUDED.iris_code,
        iris_geometry = EXCLUDED.iris_geometry,
        neighbourhood_uid = EXCLUDED.neighbourhood_uid,
        neighbour_name = EXCLUDED.neighbour_name,
        neighbourhood_geometry = EXCLUDED.neighbourhood_geometry,
        district_uid = EXCLUDED.district_uid,
        district_name = EXCLUDED.district_name,
        district_geometry = EXCLUDED.district_geometry;
    """

    template = "(" + ", ".join(
        [
            "%s",  # id
            "%s",  # latitude
            "%s",  # longitude
            "%s::jsonb",  # metadata
            "%s",  # db_row_id
            "%s",  # transaction_id
            "%s::timestamp",  # transaction_date
            "%s",  # transaction_year
            "%s",  # transaction_month
            "%s",  # transaction_quarter
            "%s",  # asset_price
            "%s",  # asset_surface
            "%s",  # asset_psqm
            "%s",  # asset_rooms
            "%s",  # asset_floor
            "%s",  # asset_type
            "ST_SetSRID(ST_GeomFromText(%s), 4326)",  # asset_geometry
            "%s",  # asset_latitude
            "%s",  # asset_longitude
            "%s",  # asset_hashed_title
            "%s",  # land_hashed_title
            "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END",  # land_geometry
            "%s",  # ilot_uid
            "%s",  # ilot_objectid
            "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END",  # ilot_geometry
            "%s",  # iris_uid
            "%s",  # iris_code
            "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END",  # iris_geometry
            "%s",  # neighbourhood_uid
            "%s",  # neighbour_name
            "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END",  # neighbourhood_geometry
            "%s",  # district_uid
            "%s",  # district_name
            "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END",  # district_geometry
        ]
    ) + ")"

    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            adapted_chunk = []
            for row in chunk:
                (
                    id_val,
                    latitude,
                    longitude,
                    metadata,
                    db_row_id,
                    transaction_id,
                    transaction_date,
                    transaction_year,
                    transaction_month,
                    transaction_quarter,
                    asset_price,
                    asset_surface,
                    asset_psqm,
                    asset_rooms,
                    asset_floor,
                    asset_type,
                    asset_geometry,
                    asset_latitude,
                    asset_longitude,
                    asset_hashed_title,
                    land_hashed_title,
                    land_geometry,
                    ilot_uid,
                    ilot_objectid,
                    ilot_geometry,
                    iris_uid,
                    iris_code,
                    iris_geometry,
                    neighbourhood_uid,
                    neighbour_name,
                    neighbourhood_geometry,
                    district_uid,
                    district_name,
                    district_geometry,
                ) = row

                adapted_chunk.append(
                    (
                        id_val,
                        latitude,
                        longitude,
                        metadata,
                        db_row_id,
                        transaction_id,
                        transaction_date,
                        transaction_year,
                        transaction_month,
                        transaction_quarter,
                        asset_price,
                        asset_surface,
                        asset_psqm,
                        asset_rooms,
                        asset_floor,
                        asset_type,
                        asset_geometry,
                        asset_latitude,
                        asset_longitude,
                        asset_hashed_title,
                        land_hashed_title,
                        land_geometry,
                        land_geometry,
                        ilot_uid,
                        ilot_objectid,
                        ilot_geometry,
                        ilot_geometry,
                        iris_uid,
                        iris_code,
                        iris_geometry,
                        iris_geometry,
                        neighbourhood_uid,
                        neighbour_name,
                        neighbourhood_geometry,
                        neighbourhood_geometry,
                        district_uid,
                        district_name,
                        district_geometry,
                        district_geometry,
                    )
                )

            execute_values(cur, sql, adapted_chunk, template=template, page_size=chunk_size)
            total += len(chunk)
    conn.commit()
    return total


def load_parquet(parquet_path: Path, chunk_size: int) -> tuple[int, int]:
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    try:
        ensure_target_schema(conn)

        df = pd.read_parquet(parquet_path)
        missing = [c for c in ["transaction_id", "asset_latitude", "asset_longitude"] if c not in df.columns]
        if missing:
            raise ValueError(
                "Parquet is missing required columns for properties ingestion: "
                + ", ".join(missing)
            )

        records = df.to_dict(orient="records")
        rows: list[tuple[Any, ...]] = []
        skipped = 0
        for rec in records:
            row = _record_to_row(rec)
            if row is None:
                skipped += 1
                continue
            rows.append(row)

        if rows:
            loaded = upsert_rows(conn, rows, chunk_size=chunk_size)
        else:
            loaded = 0
        return loaded, skipped
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand production.properties and ingest a transaction Parquet file."
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
    args = parse_args()
    parquet_path = Path(args.parquet).expanduser().resolve()
    if not parquet_path.exists():
        print(f"Parquet file not found: {parquet_path}", file=sys.stderr)
        return 1

    try:
        loaded, skipped = load_parquet(parquet_path, chunk_size=args.chunk_size)
        print(f"Loaded/updated rows: {loaded}")
        print(f"Skipped rows (invalid/missing coords or id): {skipped}")
        if shapely_wkb is None:
            print(
                "Note: shapely is not installed; binary geometry values in parquet were ignored unless text/WKT.",
                file=sys.stderr,
            )
        return 0
    except Exception as exc:
        print(f"Parquet load failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

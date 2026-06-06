"""Download Morocco national boundary from OSM and update geo.land.

Replaces the rough Natural Earth polygon with the actual OSM boundary polygon
that precisely follows both the coastline and inland borders. Once geo.land
is high-res, the ST_Contains classifier in the score's coastal correction is
accurate to the coastline level.

Usage:
    python scripts/ingest/load_osm_land.py
"""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import psycopg2  # noqa: E402
import requests  # noqa: E402

from app.core.config import get_settings  # noqa: E402

_settings = get_settings()

HEADERS = {
    "Accept": "application/json",
    "User-Agent": _settings.overpass_user_agent,
}

# Outer ways of Morocco's national boundary relation.
QUERY = f"""
[out:json][timeout:{_settings.overpass_query_timeout_s}];
relation({_settings.osm_morocco_relation_id});
way(r:"outer");
out geom;
"""


def create_table_if_not_exists(conn):
    """Create geo schema and land table if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS geo")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS geo.land (
                id SERIAL PRIMARY KEY,
                name TEXT,
                geom GEOMETRY(MULTIPOLYGON, 4326)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_land_geom ON geo.land USING GIST(geom)"
        )
    conn.commit()


def main() -> int:
    """Download the Morocco boundary from Overpass and replace ``geo.land``."""
    database_url = _settings.database_url

    print(
        f"Fetching Morocco boundary (OSM relation {_settings.osm_morocco_relation_id}) "
        "from Overpass ..."
    )
    try:
        resp = requests.post(
            _settings.overpass_url,
            data=QUERY,
            timeout=_settings.overpass_http_timeout_s,
            headers=HEADERS,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Overpass error: {exc}", file=sys.stderr)
        return 1

    elements = resp.json().get("elements", [])
    outer = [el for el in elements if el.get("type") == "way"]
    print(f"Outer ways: {len(outer)}")
    if not outer:
        print("No outer ways found", file=sys.stderr)
        return 1

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    try:
        create_table_if_not_exists(conn)
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _bnd (geom geometry(LineString, 4326)) ON COMMIT DROP"
            )
            n = 0
            for way in outer:
                nodes = way.get("geometry", [])
                if len(nodes) < 2:
                    continue
                coords = ", ".join(f"{nd['lon']} {nd['lat']}" for nd in nodes)
                cur.execute(
                    "INSERT INTO _bnd VALUES (ST_GeomFromText(%s, 4326))",
                    (f"LINESTRING({coords})",),
                )
                n += 1
            print(f"Inserted {n} way segments")

            cur.execute(
                "SELECT ST_NPoints(ST_LineMerge(ST_Union(geom))), "
                "ST_IsClosed(ST_LineMerge(ST_Union(geom))) FROM _bnd"
            )
            npts, closed = cur.fetchone()
            print(f"Merged ring: {npts} points, closed={closed}")

            if not closed:
                print("Ring not closed -- cannot build polygon", file=sys.stderr)
                conn.rollback()
                return 1

            cur.execute("DELETE FROM geo.land")
            cur.execute(
                "INSERT INTO geo.land (name, geom) "
                "SELECT %s, ST_Multi(ST_MakeValid("
                "    ST_MakePolygon(ST_LineMerge(ST_Union(geom)))"
                ")) FROM _bnd",
                ("osm_boundary",),
            )
            cur.execute(
                "SELECT ST_NPoints(geom), "
                "ROUND((ST_Area(geom::geography)/1e6)::numeric, 0) FROM geo.land"
            )
            pts, km2 = cur.fetchone()
            print(f"geo.land updated: {pts} points, {km2} km2")
            conn.commit()
        return 0
    except Exception:
        conn.rollback()
        import traceback

        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

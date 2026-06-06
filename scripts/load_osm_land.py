"""Download Morocco national boundary from OSM (relation 3630439) and update
geo.land with a high-resolution polygon.

This replaces the rough Natural Earth polygon (~1000 pts, ~1-5 km coastal error)
with the actual OSM boundary polygon (~50k+ pts) that precisely follows both the
coastline and the inland borders.  Once geo.land is high-res, the ST_Contains
classifier in _land_buffer_fraction_db() is accurate at the coastline level.

Usage:
    python scripts/load_osm_land.py
"""
import sys
from pathlib import Path

import psycopg2
import requests

# Ensure backend package is importable
_backend_root = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from app.config import get_settings  # noqa: E402

_settings = get_settings()

# Overpass requires an identifiable User-Agent
HEADERS = {
    "Accept": "application/json",
    "User-Agent": _settings.overpass_user_agent,
}

# Query only the outer ways of Morocco's national boundary relation (faster).
QUERY = f"""
[out:json][timeout:{_settings.overpass_query_timeout_s}];
relation({_settings.osm_morocco_relation_id});
way(r:"outer");
out geom;
"""


def create_table_if_not_exists(conn):
    """Create geo schema and land table if they don't exist."""
    with conn.cursor() as cur:
        # Create schema if it doesn't exist
        cur.execute("CREATE SCHEMA IF NOT EXISTS geo")
        
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo.land (
                id SERIAL PRIMARY KEY,
                name TEXT,
                geom GEOMETRY(MULTIPOLYGON, 4326)
            )
        """)
        # Create spatial index if it doesn't exist
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_land_geom 
            ON geo.land USING GIST(geom)
        """)
    conn.commit()


def main() -> int:
    """Download the Morocco boundary from Overpass and replace ``geo.land``.

    Returns 0 on success, non-zero on Overpass / DB failure or when the
    boundary ring cannot be closed into a valid polygon.
    """
    database_url = _settings.database_url

    print(
        f"Fetching Morocco boundary (OSM relation {_settings.osm_morocco_relation_id}) "
        f"from Overpass ..."
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
    # The query returns way elements directly (not wrapped in a relation)
    outer = [el for el in elements if el.get("type") == "way"]
    print(f"Outer ways: {len(outer)}")
    if not outer:
        print("No outer ways found", file=sys.stderr)
        return 1

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    try:
        # Create table if it doesn't exist
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
                coords = ", ".join(
                    f"{nd['lon']} {nd['lat']}" for nd in nodes
                )
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
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

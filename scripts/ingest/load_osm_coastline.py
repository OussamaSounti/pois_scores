"""Replace geo.coastline with high-resolution OSM coastline for Morocco.

Downloads coastline ways from the Overpass API and inserts them as
individual rows.

Usage:
    python scripts/ingest/load_osm_coastline.py
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

BBOX = _settings.osm_morocco_bbox

QUERY = f"""
[out:json][timeout:{_settings.overpass_query_timeout_s}][bbox:{BBOX}];
way["natural"="coastline"];
out geom;
"""

HEADERS = {
    "Accept": "application/json",
    "User-Agent": _settings.overpass_user_agent,
}


def create_table_if_not_exists(conn):
    """Create geo schema and coastline table if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS geo")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS geo.coastline (
                id SERIAL PRIMARY KEY,
                name TEXT,
                geom GEOMETRY(MULTILINESTRING, 4326)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_coastline_geom ON geo.coastline USING GIST(geom)"
        )
    conn.commit()


def main() -> int:
    """Replace ``geo.coastline`` with the latest OSM coastline ways for Morocco."""
    database_url = _settings.database_url

    print("Querying Overpass API for Morocco coastline ways ...")
    print(f"  BBOX  : {BBOX}")
    try:
        resp = requests.post(
            _settings.overpass_url,
            data={"data": QUERY},
            timeout=_settings.overpass_http_timeout_s,
            headers=HEADERS,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Overpass API error: {exc}", file=sys.stderr)
        return 1

    ways = [el for el in resp.json().get("elements", []) if el.get("type") == "way"]
    print(f"Received {len(ways)} coastline ways from Overpass")
    if not ways:
        print("No ways returned -- check bbox or Overpass availability", file=sys.stderr)
        return 1

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    try:
        create_table_if_not_exists(conn)

        inserted = skipped = 0
        with conn.cursor() as cur:
            cur.execute("DELETE FROM geo.coastline")
            for way in ways:
                nodes = way.get("geometry", [])
                if len(nodes) < 2:
                    skipped += 1
                    continue
                coords = ", ".join(f"{n['lon']} {n['lat']}" for n in nodes)
                cur.execute(
                    "INSERT INTO geo.coastline (name, geom) "
                    "VALUES ('osm', ST_Multi(ST_GeomFromText(%s, 4326)))",
                    (f"LINESTRING({coords})",),
                )
                inserted += 1

        conn.commit()
        if skipped:
            print(f"Skipped {skipped} degenerate ways (fewer than 2 nodes)")
        print(f"Loaded {inserted} OSM coastline segments into geo.coastline")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"Error loading coastline: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

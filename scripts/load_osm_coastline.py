"""Replace geo.coastline with high-resolution OSM coastline for Morocco.

Downloads coastline ways from the Overpass API and inserts them as
individual rows, replacing the coarse Natural Earth 10 m data.

Usage:
    python scripts/load_osm_coastline.py
"""
import os
import sys

import psycopg2
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding box: south, west, north, east
BBOX = "27,-18,37,0"

QUERY = f"""
[out:json][timeout:180][bbox:{BBOX}];
way["natural"="coastline"];
out geom;
"""

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://poi_user:poi_password@localhost:5432/poi_db"
)


def main() -> int:
    print("Querying Overpass API for Morocco coastline ways ...")
    print(f"  BBOX  : {BBOX}")
    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": QUERY},
            timeout=210,
            headers={"Accept": "application/json"},
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

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    inserted = skipped = 0
    with conn.cursor() as cur:
        cur.execute("TRUNCATE geo.coastline")
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

    conn.close()
    if skipped:
        print(f"Skipped {skipped} degenerate ways (fewer than 2 nodes)")
    print(f"Loaded {inserted} OSM coastline segments into geo.coastline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
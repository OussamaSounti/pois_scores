"""
Load Morocco land polygon from Natural Earth into geo.land.

geo.land is used by the spatial service to compute the TRUE fraction of the
1 km analysis buffer that lies on land via PostGIS area intersection.  This
is accurate for capes, peninsulas, bays and other non-linear coastal shapes
where the straight-coastline formula would be wrong.

Usage:
    python scripts/load_land_polygons.py
"""

import json
import os
import urllib.request

import psycopg2

URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_10m_admin_0_countries.geojson"
)
LOCAL_CACHE = os.path.join(os.path.dirname(__file__), "..", "ne_countries.geojson")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://poi_user:poi_password@localhost:5432/poi_db"
)


def main() -> None:
    # ── Download ──────────────────────────────────────────────────────────
    if not os.path.exists(LOCAL_CACHE):
        print("Downloading Natural Earth 10m country boundaries (~25 MB)…")
        urllib.request.urlretrieve(URL, LOCAL_CACHE)
        print("Downloaded.")
    else:
        print("Using cached file:", LOCAL_CACHE)

    with open(LOCAL_CACHE, encoding="utf-8") as f:
        data = json.load(f)

    # ── Find Morocco ──────────────────────────────────────────────────────
    morocco = None
    for feat in data["features"]:
        props = feat.get("properties") or {}
        if props.get("ADM0_A3") == "MAR" or props.get("NAME") == "Morocco":
            morocco = feat
            break

    if morocco is None:
        print("ERROR: Morocco not found in dataset.")
        return

    geom = morocco["geometry"]
    # Natural Earth countries are always MultiPolygon; ensure it if not
    if geom["type"] == "Polygon":
        geom = {"type": "MultiPolygon", "coordinates": [geom["coordinates"]]}
    geom_json = json.dumps(geom)
    print(f"Morocco geometry type: {geom['type']}, "
          f"parts: {len(geom['coordinates'])}")

    # ── Load into DB ──────────────────────────────────────────────────────
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor()

        # Ensure schema + table exist (idempotent)
        cur.execute("CREATE SCHEMA IF NOT EXISTS geo")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geo.land (
                id   serial PRIMARY KEY,
                name text,
                geom geometry(MultiPolygon, 4326) NOT NULL
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_geo_land_geom ON geo.land USING GIST (geom)"
        )

        # Replace any existing Morocco polygon
        cur.execute("DELETE FROM geo.land WHERE name = 'morocco'")
        cur.execute(
            """
            INSERT INTO geo.land (name, geom)
            VALUES ('morocco', ST_Multi(ST_GeomFromGeoJSON(%s)))
            """,
            (geom_json,),
        )
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM geo.land")
        print("Rows in geo.land:", cur.fetchone()[0])
    finally:
        conn.close()

    print("Done — Morocco land polygon loaded.")


if __name__ == "__main__":
    main()

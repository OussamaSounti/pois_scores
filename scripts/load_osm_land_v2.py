"""Load a Morocco land polygon from Natural Earth 50m admin-0 boundaries.

This replaces geo.land with a clean, ocean-free polygon from a curated
natural-earth-vector GitHub release.  The polygon is used ONLY for map
visualisation (the /api/v1/geo/land overlay); score calculations no longer
depend on geo.land (they use the OSM coastline cross-product instead).

Usage:
    python scripts/load_osm_land_v2.py
"""

import json
import os
import sys

import psycopg2
import requests

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://poi_user:poi_password@localhost:5432/poi_db"
)

NE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_10m_admin_0_countries.geojson"
)


def main() -> int:
    print("Downloading Natural Earth 50m country boundaries ...")
    try:
        resp = requests.get(NE_URL, timeout=120, headers={"User-Agent": "poi-scores/1.0"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Download error: {exc}", file=sys.stderr)
        return 1

    features = resp.json().get("features", [])
    morocco = next(
        (f for f in features if f.get("properties", {}).get("ISO_A2") == "MA"),
        None,
    )
    if morocco is None:
        print("Morocco (ISO_A2=MA) not found in dataset", file=sys.stderr)
        return 1

    geom = morocco["geometry"]
    geom_str = json.dumps(geom)

    n_rings = (
        len(geom["coordinates"])
        if geom["type"] == "MultiPolygon"
        else len(geom["coordinates"])
    )
    total_pts = sum(
        len(ring)
        for part in (
            geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        )
        for ring in part
    )
    print(f"Morocco geometry: type={geom['type']}  rings={n_rings}  points={total_pts}")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE geo.land")
            cur.execute(
                "INSERT INTO geo.land (name, geom) "
                "VALUES (%s, ST_Multi(ST_MakeValid(ST_GeomFromGeoJSON(%s))))",
                ("ne_50m_morocco", geom_str),
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


import os
import sys

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://poi_user:poi_password@localhost:5432/poi_db"
)

BUILD_SQL = """
WITH
bbox AS (
    SELECT ST_SetSRID(ST_MakeEnvelope(-17.5, 27.0, 1.0, 36.5), 4326) AS geom
),
segs AS (
    SELECT (ST_Dump(ST_CollectionExtract(
        ST_Intersection(c.geom, bb.geom), 2
    ))).geom AS geom
    FROM   geo.coastline c, bbox bb
    WHERE  ST_Intersects(c.geom, bb.geom)
),
combined AS (
    SELECT geom FROM segs
    UNION ALL
    SELECT ST_ExteriorRing(bbox.geom) AS geom FROM bbox
),
polys AS (
    SELECT (ST_Dump(ST_Polygonize(geom))).geom AS geom
    FROM   combined
),
land AS (
    SELECT geom FROM polys
    WHERE  ST_Contains(geom, ST_SetSRID(ST_MakePoint(-7.59, 33.57), 4326))
)
SELECT ST_Multi(ST_MakeValid(ST_Union(geom))) AS geom,
       COUNT(*)                               AS n,
       ST_NPoints(ST_Union(geom))             AS npts,
       ROUND((ST_Area(ST_Union(geom)::geography)/1e6)::numeric, 0) AS km2
FROM   land
"""

INSERT_SQL = """
INSERT INTO geo.land (name, geom)
WITH
bbox AS (
    SELECT ST_SetSRID(ST_MakeEnvelope(-17.5, 27.0, 1.0, 36.5), 4326) AS geom
),
segs AS (
    SELECT (ST_Dump(ST_CollectionExtract(
        ST_Intersection(c.geom, bb.geom), 2
    ))).geom AS geom
    FROM   geo.coastline c, bbox bb
    WHERE  ST_Intersects(c.geom, bb.geom)
),
combined AS (
    SELECT geom FROM segs
    UNION ALL
    SELECT ST_ExteriorRing(bbox.geom) AS geom FROM bbox
),
polys AS (
    SELECT (ST_Dump(ST_Polygonize(geom))).geom AS geom
    FROM   combined
),
land AS (
    SELECT geom FROM polys
    WHERE  ST_Contains(geom, ST_SetSRID(ST_MakePoint(-7.59, 33.57), 4326))
)
SELECT 'coastline_polygon',
       ST_Multi(ST_MakeValid(ST_Union(geom)))
FROM   land
"""


def main() -> int:
    print("Building Morocco land polygon from geo.coastline segments ...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # Dry-run: check what we would get
            cur.execute(BUILD_SQL)
            row = cur.fetchone()
            if row is None or row[0] is None:
                print("No land polygon produced -- is geo.coastline populated?",
                      file=sys.stderr)
                conn.rollback()
                return 1

            _geom, n, npts, km2 = row
            print(f"  Sub-polygons merged : {n}")
            print(f"  Total points        : {npts}")
            print(f"  Area                : {km2} km2")

            if km2 > 1_000_000 or km2 < 200_000:
                print(
                    f"WARNING: area {km2} km2 looks implausible for Morocco; aborting.",
                    file=sys.stderr,
                )
                conn.rollback()
                return 1

            # Commit the new polygon
            cur.execute("TRUNCATE geo.land")
            cur.execute(INSERT_SQL)
            conn.commit()

        print("geo.land updated successfully.")
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

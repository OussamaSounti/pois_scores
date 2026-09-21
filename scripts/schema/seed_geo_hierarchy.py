"""Build geo.* hierarchy polygon tables from staging.transactions point data.

For each hierarchy level (district → neighbourhood → iris → ilot) the script
computes a convex hull of all transaction lat/lon points belonging to that zone.
This derives polygon boundaries directly from the 132k transaction dataset so
coverage is always complete.

Tables created / replaced:
  geo.districts          (uid, label, geom)
  geo.neighbourhoods     (uid, label, district_uid, geom)
  geo.iris               (uid, label, neighbourhood_uid, geom)
  geo.ilots              (uid, label, iris_uid, geom)

Usage (run once after DB is populated):
  docker-compose exec db psql -U poi_user -d poi_db -f /path/to/seed_geo_hierarchy.sql
  -- or via Python:
  DATABASE_URL=postgresql://... python scripts/schema/seed_geo_hierarchy.py
"""

import os
import sys

try:
    import psycopg2
except ImportError:
    print("psycopg2 not found — run inside the backend container or install it", file=sys.stderr)
    sys.exit(1)

SQL = """
DROP TABLE IF EXISTS geo.ilots;
DROP TABLE IF EXISTS geo.iris;
DROP TABLE IF EXISTS geo.neighbourhoods;
DROP TABLE IF EXISTS geo.districts;

CREATE TABLE geo.districts AS
SELECT
    district_uid AS uid,
    MAX(district_name) AS label,
    ST_ConvexHull(ST_Collect(ST_SetSRID(ST_MakePoint(asset_longitude, asset_latitude), 4326))) AS geom
FROM staging.transactions
WHERE district_uid IS NOT NULL AND asset_latitude IS NOT NULL AND asset_longitude IS NOT NULL
GROUP BY district_uid;
ALTER TABLE geo.districts ADD PRIMARY KEY (uid);
CREATE INDEX idx_geo_districts_geom ON geo.districts USING GIST (geom);

CREATE TABLE geo.neighbourhoods AS
SELECT
    neighbourhood_uid AS uid,
    MAX(neighbour_name) AS label,
    district_uid,
    ST_ConvexHull(ST_Collect(ST_SetSRID(ST_MakePoint(asset_longitude, asset_latitude), 4326))) AS geom
FROM staging.transactions
WHERE neighbourhood_uid IS NOT NULL AND asset_latitude IS NOT NULL AND asset_longitude IS NOT NULL
GROUP BY neighbourhood_uid, district_uid;
ALTER TABLE geo.neighbourhoods ADD PRIMARY KEY (uid);
CREATE INDEX idx_geo_neighbourhoods_geom ON geo.neighbourhoods USING GIST (geom);

CREATE TABLE geo.iris AS
SELECT
    iris_uid AS uid,
    MAX(iris_code) AS label,
    MAX(neighbourhood_uid) AS neighbourhood_uid,
    ST_ConvexHull(ST_Collect(ST_SetSRID(ST_MakePoint(asset_longitude, asset_latitude), 4326))) AS geom
FROM staging.transactions
WHERE iris_uid IS NOT NULL AND asset_latitude IS NOT NULL AND asset_longitude IS NOT NULL
GROUP BY iris_uid;
ALTER TABLE geo.iris ADD PRIMARY KEY (uid);
CREATE INDEX idx_geo_iris_geom ON geo.iris USING GIST (geom);

CREATE TABLE geo.ilots AS
SELECT
    ilot_uid AS uid,
    MAX(ilot_objectid) AS label,
    MAX(iris_uid) AS iris_uid,
    ST_ConvexHull(ST_Collect(ST_SetSRID(ST_MakePoint(asset_longitude, asset_latitude), 4326))) AS geom
FROM staging.transactions
WHERE ilot_uid IS NOT NULL AND asset_latitude IS NOT NULL AND asset_longitude IS NOT NULL
GROUP BY ilot_uid;
ALTER TABLE geo.ilots ADD PRIMARY KEY (uid);
CREATE INDEX idx_geo_ilots_geom ON geo.ilots USING GIST (geom);
"""


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SQL)
        for table in ("districts", "neighbourhoods", "iris", "ilots"):
            cur.execute(f"SELECT COUNT(*) FROM geo.{table}")
            n = cur.fetchone()[0]
            print(f"  geo.{table}: {n} zones")
    conn.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

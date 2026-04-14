"""Load Natural Earth 10m Morocco coastline into geo.coastline."""

import json
import os
import psycopg2

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "..", "ne_coastline.geojson")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://poi_user:poi_password@localhost:5432/poi_db"
)

# Morocco bounding box with a margin
LON_MIN, LON_MAX = -18.0, 0.0
LAT_MIN, LAT_MAX = 27.0, 37.0


def main() -> None:
    with open(GEOJSON_PATH) as f:
        data = json.load(f)

    morocco_lines: list[list[list[float]]] = []
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            coords = [
                c for c in geom["coordinates"]
                if LON_MIN <= c[0] <= LON_MAX and LAT_MIN <= c[1] <= LAT_MAX
            ]
            if len(coords) >= 2:
                morocco_lines.append(coords)
        elif geom["type"] == "MultiLineString":
            for line in geom["coordinates"]:
                coords = [
                    c for c in line
                    if LON_MIN <= c[0] <= LON_MAX and LAT_MIN <= c[1] <= LAT_MAX
                ]
                if len(coords) >= 2:
                    morocco_lines.append(coords)

    print(f"Found {len(morocco_lines)} coastline segments in Morocco bbox")
    if not morocco_lines:
        print("No segments found — check GeoJSON file path")
        return

    def line_wkt(coords: list[list[float]]) -> str:
        return "(" + ",".join(f"{c[0]} {c[1]}" for c in coords) + ")"

    multi_wkt = "MULTILINESTRING(" + ",".join(line_wkt(l) for l in morocco_lines) + ")"

    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor()
        # Clear old data then insert fresh
        cur.execute("DELETE FROM geo.coastline WHERE name = 'morocco'")
        cur.execute(
            "INSERT INTO geo.coastline (name, geom) VALUES ('morocco', ST_GeomFromText(%s, 4326))",
            (multi_wkt,),
        )
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM geo.coastline")
        print("Rows in geo.coastline:", cur.fetchone()[0])
    finally:
        conn.close()
    print("Done — coastline loaded.")


if __name__ == "__main__":
    main()

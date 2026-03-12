"""Apply schema_feature_pipeline.sql (properties, poi_imports, property_features). Run once after dump restore."""

import os
import sys
from pathlib import Path

# Ensure app package is importable (e.g. when run as python scripts/run_schema_feature_pipeline.py)
_app_root = Path(__file__).resolve().parent.parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

import psycopg2

from app.config import get_settings


def main() -> int:
    url = get_settings().database_url
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(script_dir, "schema_feature_pipeline.sql")
    with open(sql_path) as f:
        sql = f.read()
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.close()
        print("Pipeline schema applied successfully.")
        return 0
    except Exception as e:
        print(f"Schema apply failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

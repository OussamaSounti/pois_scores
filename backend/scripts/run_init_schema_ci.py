"""Run init_schema_ci.sql against DATABASE_URL. Used in CI to create production.pois."""

import os
import sys

import psycopg2

def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(script_dir, "init_schema_ci.sql")
    with open(sql_path) as f:
        init_sql = f.read()
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(init_sql)
        conn.close()
        return 0
    except Exception as e:
        print(f"Init schema failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

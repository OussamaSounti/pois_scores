"""Run init_schema_ci.sql against DATABASE_URL. Used in CI to create active.production_pois_current."""

import os
import sys
from pathlib import Path

import psycopg2

# Ensure app package is importable when run as python scripts/run_init_schema_ci.py
_app_root = Path(__file__).resolve().parent.parent
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

from app.config import get_settings  # noqa: E402


def main() -> int:
    """Apply ``init_schema_ci.sql`` to the configured database.

    Reads the DSN from :class:`app.config.Settings`. Returns 0 on success,
    1 if the DSN is missing or the SQL fails to execute.
    """
    url = get_settings().database_url
    if not url:
        print("Database DSN is not configured (settings.database_url is empty)", file=sys.stderr)
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

"""Apply ``init_schema_ci.sql`` to ``DATABASE_URL``.

Used in CI to create the external POI contract tables
(``active.production_pois_current``, ``history.production_poi_history``).
"""

import sys
from pathlib import Path

# Make backend/ importable when run as ``python scripts/schema/apply_init.py``.
_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import psycopg2  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    """Execute ``init_schema_ci.sql`` against the configured DSN."""
    settings = get_settings()
    if not settings.database_url:
        print("Database DSN is not configured (settings.database_url is empty)", file=sys.stderr)
        return 1
    sql_path = Path(__file__).resolve().parent / "init_schema_ci.sql"
    init_sql = sql_path.read_text()
    try:
        conn = psycopg2.connect(settings.database_url)
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

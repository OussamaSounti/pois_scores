"""Apply ``feature_pipeline.sql`` to ``DATABASE_URL``.

Run once when adding the pipeline (local/dev) or whenever ``production.*`` /
``geo.*`` tables need to be (re-)created.
"""

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import psycopg2  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    """Execute pipeline schema SQL files against the configured DSN."""
    settings = get_settings()
    if not settings.database_url:
        print("Database DSN is not configured (settings.database_url is empty)", file=sys.stderr)
        return 1
    schema_dir = Path(__file__).resolve().parent
    sql_files = (
        schema_dir / "feature_pipeline.sql",
        schema_dir / "feature_pipeline_runs.sql",
    )
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            for sql_path in sql_files:
                cur.execute(sql_path.read_text(encoding="utf-8"))
        conn.close()
        print("Pipeline schema applied successfully.")
        return 0
    except Exception as e:
        print(f"Schema apply failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

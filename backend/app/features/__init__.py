"""Feature-based domain modules.

Each subpackage owns one feature end-to-end (router, schemas, service, SQL).
Cross-feature imports are allowed only between scoring (``scores``,
``pois``, ``feature_pipeline``) since they form a tightly-coupled domain;
``geo`` is standalone.

**Dependency rule:** ``app.core`` is the foundation layer. Feature modules may
import from ``app.core``, but ``app.core`` must **never** import from
``app.features``. Shared constants live in ``app.core.constants``.
"""

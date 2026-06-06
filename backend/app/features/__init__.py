"""Feature-based domain modules.

Each subpackage owns one feature end-to-end (router, schemas, service, model,
SQL). Cross-feature imports are allowed only between scoring (``scores``,
``pois``, ``feature_pipeline``) since they form a tightly-coupled domain;
``properties``, ``geo`` and ``health`` are otherwise standalone.

No feature module may be imported from ``app.core``.
"""

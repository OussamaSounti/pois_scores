"""Feature pipeline — the two scoring flows that populate ``production.property_features``.

Two distinct, operationally-independent flows share a math/upsert core:

- :mod:`historical_batch` — manual one-shot backfill that scores every
  property with a ``transaction_date`` against ``history.production_poi_history``
  at that exact date. Large chunks; long-running. ``poi_source = 'history'``.
- :mod:`weekly_continuous` — Prefect-scheduled weekly delta that scores
  newly-arrived properties (no existing feature row) against
  ``active.production_pois_current``. Small chunks; fast.
  ``poi_source = 'current'``.

Both flows call into :mod:`app.features.scores.service` for the actual math
and into :mod:`db_utils` for the chunked write to ``production.property_features``.
"""

from app.features.feature_pipeline.historical_batch import run_historical_batch
from app.features.feature_pipeline.weekly_continuous import run_weekly_continuous

__all__ = ["run_historical_batch", "run_weekly_continuous"]

"""POI feature: HTTP listing endpoint and POI-table queries.

Owns every read against the external contract tables
``active.production_pois_current`` (flat current snapshot) and
``history.production_poi_history`` (SCD2, requires ``is_canonical = true``).
"""

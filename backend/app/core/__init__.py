"""Cross-cutting kernel: settings, DB session, metrics, domain constants, geo primitives.

Anything that is not specific to a single feature lives here. Feature modules
(`app.features.*`) import from this package; nothing in `core/` may import
from `features/`.
"""

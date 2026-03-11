"""Pytest configuration and fixtures."""

import os

# Run from repo root or backend/; ensure app is importable
os.environ.setdefault("PYTHONPATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

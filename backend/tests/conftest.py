"""Pytest configuration and fixtures."""

import os

import pytest

# Run from repo root or backend/; ensure app is importable
os.environ.setdefault("PYTHONPATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

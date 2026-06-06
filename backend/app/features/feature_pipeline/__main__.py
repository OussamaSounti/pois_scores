"""CLI dispatcher for the two pipeline flows.

Usage:

    python -m app.features.feature_pipeline weekly_continuous [--chunk-size N]
    python -m app.features.feature_pipeline historical_batch  [--chunk-size N]

The flow name is the first positional argument; everything else is parsed as
flow-specific options.
"""

from __future__ import annotations

import argparse
import sys

from app.core.constants import CHUNK_SIZE
from app.features.feature_pipeline.historical_batch import (
    DEFAULT_CHUNK_SIZE as HISTORICAL_CHUNK_SIZE,
)
from app.features.feature_pipeline.historical_batch import (
    main as historical_main,
)
from app.features.feature_pipeline.weekly_continuous import main as weekly_main

_FLOWS = {"weekly_continuous", "historical_batch"}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.features.feature_pipeline",
        description="Dispatch a feature pipeline flow.",
    )
    parser.add_argument(
        "flow",
        choices=sorted(_FLOWS),
        help="Which flow to run.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Optional chunk size override (defaults: weekly=%d, historical=%d)."
        % (CHUNK_SIZE, HISTORICAL_CHUNK_SIZE),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.flow == "weekly_continuous":
        weekly_main(chunk_size=args.chunk_size or CHUNK_SIZE)
    else:  # historical_batch
        historical_main(chunk_size=args.chunk_size or HISTORICAL_CHUNK_SIZE)


if __name__ == "__main__":
    main()

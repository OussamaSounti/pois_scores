"""Pipeline progress tracker with ETA and throughput logging."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks chunk-level progress and logs ETA / throughput metrics."""

    def __init__(self, total: int, flow_name: str) -> None:
        self._total = total
        self._flow_name = flow_name
        self._processed = 0
        self._start = time.monotonic()

    def log_chunk(self, chunk_index: int, chunk_rows: int, chunk_elapsed_s: float) -> None:
        self._processed += chunk_rows
        wall = time.monotonic() - self._start
        rate = self._processed / wall if wall > 0 else 0
        pct = (self._processed / self._total * 100) if self._total > 0 else 100
        remaining = (self._total - self._processed) / rate if rate > 0 else 0
        eta_min = remaining / 60

        logger.info(
            "[%s chunk %d] %d/%d (%.1f%%) | %.1f prop/s | chunk %.2fs | ETA %.0fmin",
            self._flow_name,
            chunk_index,
            self._processed,
            self._total,
            pct,
            rate,
            chunk_elapsed_s,
            eta_min,
        )

    def log_done(self, processed: int, skipped: int) -> None:
        wall = time.monotonic() - self._start
        logger.info(
            "[%s] Done: processed=%d skipped=%d total_time=%.1fs (%.1f prop/s)",
            self._flow_name,
            processed,
            skipped,
            wall,
            processed / wall if wall > 0 else 0,
        )

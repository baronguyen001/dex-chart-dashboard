"""Timeframe definitions.

GeckoTerminal's OHLCV endpoint only serves a fixed set of resolution/aggregate pairs
(verified against the public API):

    minute -> 1, 5, 15    |    hour -> 1, 4, 12    |    day -> 1

So **30m and 2h are not native** — the dashboard fetches the next finer native frame
(15m for 30m, 1h for 2h) and resamples it into fixed-width buckets locally. ``limit`` is
candles-per-fetch (GeckoTerminal caps it at 1000).
"""

from __future__ import annotations

# Chart timeframes offered in the UI, coarsest selection logic in chart.py.
CHART_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d")

TIMEFRAME_SPECS: dict[str, dict] = {
    "1m": {"resolution": "minute", "aggregate": 1, "limit": 1000},  # ~16h (gecko max limit)
    "5m": {"resolution": "minute", "aggregate": 5, "limit": 288},  # ~1 day
    "15m": {"resolution": "minute", "aggregate": 15, "limit": 192},  # ~2 days
    "30m": {"derive_from": "15m", "period_sec": 1800},  # 15m x2, resampled
    "1h": {"resolution": "hour", "aggregate": 1, "limit": 240},  # ~10 days
    "2h": {"derive_from": "1h", "period_sec": 7200},  # 1h x2, resampled
    "4h": {"resolution": "hour", "aggregate": 4, "limit": 240},  # ~40 days
    "1d": {"resolution": "day", "aggregate": 1, "limit": 365},  # ~1 year (thin-data fallback)
}

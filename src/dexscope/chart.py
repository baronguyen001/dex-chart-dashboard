"""Build the chart payload the frontend renders (Chart.js candlesticks + level lines).

Kept deliberately generic: candles come from GeckoTerminal, and the only overlays are
the user's own ``entry``/``sl``/``tp1``/``tp2`` price levels drawn as horizontal lines.
(Position PnL, ladder simulation, and signal scoring are out of scope — see the README.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from .gecko import GeckoClient
from .models import CHART_TIMEFRAMES
from .util import to_float

LEVEL_KEYS = ("entry", "sl", "tp1", "tp2")

# When auto-selecting the default timeframe, prefer these (in order) if they have enough
# candles to be readable; otherwise fall back to whichever frame has the most candles.
_PREFERRED = ("1h", "15m", "5m", "1m", "4h", "30m", "2h", "1d")
_READABLE_MIN = 20


def merge_candles(*series_list: list[dict]) -> list[dict]:
    """Merge candle series by timestamp, filling missing OHLCV fields from later series."""
    merged: dict[int, dict] = {}
    for series in series_list:
        for row in series or []:
            ts = row.get("ts")
            if ts is None:
                continue
            ts_int = int(ts)
            candidate = {
                "ts": ts_int,
                "open": to_float(row.get("open")),
                "high": to_float(row.get("high")),
                "low": to_float(row.get("low")),
                "close": to_float(row.get("close")),
                "volume": to_float(row.get("volume")),
            }
            current = merged.get(ts_int)
            if current is None:
                merged[ts_int] = candidate
                continue
            for key, value in candidate.items():
                if current.get(key) is None and value is not None:
                    current[key] = value
    return sorted(merged.values(), key=lambda row: row["ts"])


def _labels(candles: list[dict]) -> list[str]:
    return [
        datetime.fromtimestamp(int(row["ts"]), tz=timezone.utc).strftime("%m-%d %H:%M")
        for row in candles
    ]


def build_chart_frame(candles: list[dict], levels: dict[str, float | None], timeframe: str) -> dict:
    """One timeframe's worth of arrays for Chart.js, plus flat level lines."""
    labels = _labels(candles)
    has_chart = bool(candles)

    def level_series(value: float | None) -> list[float | None]:
        return [value] * len(labels) if value is not None and labels else []

    return {
        "timeframe": timeframe,
        "has_chart": has_chart,
        "has_ohlc": has_chart,
        "labels": labels,
        "open": [row.get("open") for row in candles],
        "high": [row.get("high") for row in candles],
        "low": [row.get("low") for row in candles],
        "close": [row.get("close") for row in candles],
        "volume": [row.get("volume") for row in candles],
        "levels": {key: level_series(levels.get(key)) for key in LEVEL_KEYS},
    }


def _empty_frame(timeframe: str) -> dict:
    return {
        "timeframe": timeframe,
        "has_chart": False,
        "has_ohlc": False,
        "labels": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
        "levels": {key: [] for key in LEVEL_KEYS},
    }


def build_chart_bundle(gecko: GeckoClient, item: dict) -> dict:
    """Fetch every timeframe for a watchlist item and pick a sensible default frame."""
    chain = item.get("chain") or ""
    pool = item.get("pool") or ""
    levels = {key: to_float(item.get(key)) for key in LEVEL_KEYS}

    timeframes: dict[str, dict] = {}
    summary: list[dict] = []
    for tf in CHART_TIMEFRAMES:
        candles = gecko.fetch(chain, pool, tf) if pool else []
        frame = build_chart_frame(candles, levels, tf)
        if frame["has_chart"]:
            timeframes[tf] = frame
        summary.append(
            {"timeframe": tf, "count": len(frame["labels"]), "available": frame["has_chart"]}
        )

    def count(tf: str) -> int:
        return len((timeframes.get(tf) or {}).get("labels") or [])

    selected = next(
        (tf for tf in _PREFERRED if tf in timeframes and count(tf) >= _READABLE_MIN), None
    )
    if not selected:
        selected = max(timeframes, key=count) if timeframes else "1h"

    frame = dict(timeframes.get(selected) or _empty_frame(selected))
    frame["selected_timeframe"] = selected
    frame["available_timeframes"] = [s["timeframe"] for s in summary if s["available"]]
    frame["timeframes"] = timeframes
    frame["timeframe_summary"] = summary
    return frame

"""Offline OHLCV serializers for public GeckoTerminal candle data."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .util import to_float

CANDLE_COLUMNS = ("ts", "open", "high", "low", "close", "volume")


def _normalized_candle(row: dict[str, Any]) -> dict[str, int | float | None]:
    ts = row.get("ts")
    return {
        "ts": int(ts) if ts is not None else None,
        "open": to_float(row.get("open")),
        "high": to_float(row.get("high")),
        "low": to_float(row.get("low")),
        "close": to_float(row.get("close")),
        "volume": to_float(row.get("volume")),
    }


def candles_to_csv(candles: list[dict]) -> str:
    """Serialize candles to CSV with stable OHLCV column order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CANDLE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in candles:
        writer.writerow(_normalized_candle(row))
    return buf.getvalue()


def candles_to_json(candles: list[dict]) -> str:
    """Serialize candles to JSON with stable OHLCV key order."""
    rows = [_normalized_candle(row) for row in candles]
    return json.dumps(rows, indent=2, ensure_ascii=False)

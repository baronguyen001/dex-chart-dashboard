"""Offline OHLCV serializers for public GeckoTerminal candle data."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .util import to_float

CANDLE_COLUMNS = ("ts", "open", "high", "low", "close", "volume")

_MACD_COLUMNS = (("macd", "macd"), ("signal", "macd_signal"), ("histogram", "macd_hist"))
_BOLLINGER_COLUMNS = (("middle", "bb_middle"), ("upper", "bb_upper"), ("lower", "bb_lower"))


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


def _period_columns(series: dict, prefix: str) -> list[tuple[str, list[float | None]]]:
    """Flatten a ``{period: values}`` overlay, ordering periods numerically."""
    ordered: list[tuple[int, str]] = []
    for key in series:
        try:
            ordered.append((int(key), key))
        except (TypeError, ValueError):
            continue
    return [(f"{prefix}_{period}", series[key]) for period, key in sorted(ordered)]


def _named_columns(
    series: dict, names: tuple[tuple[str, str], ...]
) -> list[tuple[str, list[float | None]]]:
    """Flatten a fixed-key overlay in declaration order, skipping absent keys."""
    return [(column, series[key]) for key, column in names if series.get(key) is not None]


def indicator_columns(indicators: dict | None) -> list[tuple[str, list[float | None]]]:
    """Flatten indicator overlays into ordered ``(column, values)`` pairs.

    Order is stable: EMA periods ascending, then RSI periods ascending, then the
    MACD triplet, then the Bollinger bands. Non-numeric period keys are skipped
    rather than raising.
    """
    if not indicators:
        return []
    columns: list[tuple[str, list[float | None]]] = []
    columns += _period_columns(indicators.get("ema") or {}, "ema")
    columns += _period_columns(indicators.get("rsi") or {}, "rsi")
    columns += _named_columns(indicators.get("macd") or {}, _MACD_COLUMNS)
    columns += _named_columns(indicators.get("bollinger") or {}, _BOLLINGER_COLUMNS)
    return columns


def _with_indicators(
    row: dict[str, Any], index: int, columns: list[tuple[str, list[float | None]]]
) -> dict[str, Any]:
    enriched: dict[str, Any] = dict(_normalized_candle(row))
    for name, values in columns:
        enriched[name] = values[index] if index < len(values) else None
    return enriched


def candles_to_csv(candles: list[dict], *, indicators: dict | None = None) -> str:
    """Serialize candles to CSV with stable OHLCV column order.

    Indicator columns, when supplied, follow the OHLCV ones and are padded with
    empty cells wherever an overlay is shorter than the candle list.
    """
    columns = indicator_columns(indicators)
    fieldnames = list(CANDLE_COLUMNS) + [name for name, _ in columns]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for index, row in enumerate(candles):
        writer.writerow(_with_indicators(row, index, columns))
    return buf.getvalue()


def candles_to_json(candles: list[dict], *, indicators: dict | None = None) -> str:
    """Serialize candles to JSON with stable OHLCV key order.

    Indicator keys, when supplied, follow the OHLCV ones and hold ``null``
    wherever an overlay is shorter than the candle list.
    """
    columns = indicator_columns(indicators)
    rows = [_with_indicators(row, index, columns) for index, row in enumerate(candles)]
    return json.dumps(rows, indent=2, ensure_ascii=False)

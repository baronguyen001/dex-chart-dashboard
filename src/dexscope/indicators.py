"""Dependency-free technical overlays computed from public OHLCV candles.

These helpers are deterministic read-only math over candle closes. They do not produce
signals, rankings, recommendations, or account-specific tracking data.
"""

from __future__ import annotations

from .util import to_float


def _close_values(candles: list[dict]) -> list[float | None]:
    return [to_float(row.get("close")) for row in candles]


def ema_values(values: list[float | None], period: int) -> list[float | None]:
    """Exponential moving average seeded from the first available close."""
    if period <= 0:
        raise ValueError("EMA period must be positive")

    multiplier = 2.0 / (period + 1)
    state: float | None = None
    out: list[float | None] = []
    for raw in values:
        value = to_float(raw)
        if value is None:
            out.append(None)
            continue
        state = value if state is None else ((value - state) * multiplier) + state
        out.append(state)
    return out


def rsi_values(values: list[float | None], period: int = 14) -> list[float | None]:
    """Wilder RSI with ``None`` until enough contiguous closes are available."""
    if period <= 0:
        raise ValueError("RSI period must be positive")

    out: list[float | None] = []
    window: list[float] = []
    avg_gain: float | None = None
    avg_loss: float | None = None
    previous: float | None = None

    for raw in values:
        value = to_float(raw)
        if value is None:
            previous = None
            window = []
            avg_gain = None
            avg_loss = None
            out.append(None)
            continue

        if previous is None:
            previous = value
            out.append(None)
            continue

        change = value - previous
        previous = value
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if avg_gain is None or avg_loss is None:
            window.append(change)
            if len(window) < period:
                out.append(None)
                continue
            gains = [max(delta, 0.0) for delta in window[-period:]]
            losses = [max(-delta, 0.0) for delta in window[-period:]]
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period

        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100.0 - (100.0 / (1.0 + rs)))

    return out


def build_indicators(
    candles: list[dict],
    *,
    ema_periods: tuple[int, ...] = (9, 21),
    rsi_period: int = 14,
) -> dict:
    """Return chart-ready overlay arrays aligned to ``candles``."""
    closes = _close_values(candles)
    return {
        "ema": {str(period): ema_values(closes, period) for period in ema_periods},
        "rsi": {str(rsi_period): rsi_values(closes, rsi_period)},
    }

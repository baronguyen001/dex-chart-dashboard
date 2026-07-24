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


def macd_values(
    values: list[float | None],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    """MACD line, signal line, and histogram, each aligned to ``values``."""
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("MACD periods must be positive")
    if fast >= slow:
        raise ValueError("MACD fast period must be shorter than the slow period")

    fast_ema = ema_values(values, fast)
    slow_ema = ema_values(values, slow)

    macd_line: list[float | None] = []
    for quick, slow_point in zip(fast_ema, slow_ema, strict=True):
        if quick is None or slow_point is None:
            macd_line.append(None)
        else:
            macd_line.append(quick - slow_point)

    signal_line = ema_values(macd_line, signal)
    histogram: list[float | None] = []
    for line, smoothed in zip(macd_line, signal_line, strict=True):
        if line is None or smoothed is None:
            histogram.append(None)
        else:
            histogram.append(line - smoothed)

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_values(
    values: list[float | None],
    period: int = 20,
    num_std: float = 2.0,
) -> dict[str, list[float | None]]:
    """Bollinger bands over the last ``period`` contiguous closes.

    The middle band is a simple moving average and the outer bands sit
    ``num_std`` population standard deviations away. A ``None`` close resets the
    window so gaps never blend across missing data.
    """
    if period <= 0:
        raise ValueError("Bollinger period must be positive")
    if num_std < 0:
        raise ValueError("Bollinger num_std must be non-negative")

    middle: list[float | None] = []
    upper: list[float | None] = []
    lower: list[float | None] = []
    window: list[float] = []

    for raw in values:
        value = to_float(raw)
        if value is None:
            window.clear()
            middle.append(None)
            upper.append(None)
            lower.append(None)
            continue

        window.append(value)
        if len(window) > period:
            window.pop(0)
        if len(window) < period:
            middle.append(None)
            upper.append(None)
            lower.append(None)
            continue

        mean = sum(window) / period
        variance = sum((point - mean) ** 2 for point in window) / period
        deviation = variance**0.5
        middle.append(mean)
        upper.append(mean + (num_std * deviation))
        lower.append(mean - (num_std * deviation))

    return {"middle": middle, "upper": upper, "lower": lower}


def build_indicators(
    candles: list[dict],
    *,
    ema_periods: tuple[int, ...] = (9, 21),
    rsi_period: int = 14,
    macd: tuple[int, int, int] | None = None,
    bollinger: tuple[int, float] | None = None,
) -> dict:
    """Return chart-ready overlay arrays aligned to ``candles``.

    ``macd`` and ``bollinger`` are opt-in: their keys are always present so the
    shape stays predictable, but they hold an empty dict unless a period tuple
    is supplied.
    """
    closes = _close_values(candles)
    return {
        "ema": {str(period): ema_values(closes, period) for period in ema_periods},
        "rsi": {str(rsi_period): rsi_values(closes, rsi_period)},
        "macd": macd_values(closes, *macd) if macd is not None else {},
        "bollinger": bollinger_values(closes, *bollinger) if bollinger is not None else {},
    }

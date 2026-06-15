"""PNG snapshot export for chart candles.

Matplotlib is an optional dependency. Core dashboard usage remains keyless and limited to
the base Flask/httpx dependencies.
"""

from __future__ import annotations

from pathlib import Path

from .indicators import build_indicators
from .util import to_float

VIZ_EXTRA_MESSAGE = "install dexscope[viz] to export PNG"


def export_snapshot(
    candles: list[dict],
    out: Path,
    *,
    title: str = "dexscope chart",
    timeframe: str = "1h",
    ema_periods: tuple[int, ...] = (),
    rsi_period: int | None = None,
) -> Path:
    """Render candles and optional EMA/RSI overlays to ``out``."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError as exc:  # pragma: no cover - exercised only without optional extra
        raise RuntimeError(VIZ_EXTRA_MESSAGE) from exc

    if not candles:
        raise ValueError("no candles available for snapshot")

    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = [row for row in candles if row.get("close") is not None]
    x_values = list(range(len(rows)))
    closes = [to_float(row.get("close")) for row in rows]
    indicators = build_indicators(rows, ema_periods=ema_periods, rsi_period=rsi_period or 14)

    use_rsi = rsi_period is not None
    if use_rsi:
        fig, (ax_price, ax_rsi) = plt.subplots(
            2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
        )
    else:
        fig, ax_price = plt.subplots(figsize=(11, 6))
        ax_rsi = None

    for i, row in enumerate(rows):
        open_price = to_float(row.get("open"))
        high = to_float(row.get("high"))
        low = to_float(row.get("low"))
        close = to_float(row.get("close"))
        if open_price is None or high is None or low is None or close is None:
            continue
        color = "#16a34a" if close >= open_price else "#dc2626"
        ax_price.vlines(i, low, high, color=color, linewidth=1)
        bottom = min(open_price, close)
        height = abs(close - open_price)
        ax_price.add_patch(
            Rectangle(
                (i - 0.32, bottom),
                0.64,
                height if height > 0 else max(abs(close) * 0.002, 0.00000001),
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
                alpha=0.85,
            )
        )

    if closes:
        ax_price.plot(x_values, closes, color="#334155", linewidth=0.8, alpha=0.35, label="Close")

    for period, values in indicators["ema"].items():
        if not ema_periods:
            break
        ax_price.plot(x_values, values, linewidth=1.4, label=f"EMA {period}")

    if use_rsi and ax_rsi is not None:
        values = next(iter(indicators["rsi"].values()), [])
        ax_rsi.plot(x_values, values, color="#7c3aed", linewidth=1.2, label=f"RSI {rsi_period}")
        ax_rsi.axhline(70, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax_rsi.axhline(30, color="#94a3b8", linewidth=0.8, linestyle="--")
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel("RSI")
        ax_rsi.grid(True, alpha=0.18)
        ax_rsi.legend(loc="upper left")

    ax_price.set_title(f"{title} - {timeframe}")
    ax_price.set_ylabel("Price")
    ax_price.grid(True, alpha=0.18)
    ax_price.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out

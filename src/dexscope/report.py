"""Read-only terminal report rows for a whole watchlist.

The report combines public DexScreener prices with local EMA/RSI math over public
OHLCV candles. It is a deterministic digest, not a signal engine or ranking system.
"""

from __future__ import annotations

from .alerts import evaluate_levels
from .formatting import money, price
from .util import to_float
from .watchlist import build_items


def _last_value(values: list[float | None] | None) -> float | None:
    for value in reversed(values or []):
        parsed = to_float(value)
        if parsed is not None:
            return parsed
    return None


def build_report_rows(
    watchlist: list[dict],
    live: dict[str, dict],
    indicators_by_key: dict[str, dict],
) -> list[dict]:
    """Join watchlist, live prices, latest indicators, and nearest user level distance."""
    rows: list[dict] = []
    for item in build_items(watchlist, live):
        indicators = indicators_by_key.get(item["key"]) or {}
        ema = indicators.get("ema") or {}
        rsi = indicators.get("rsi") or {}
        verdict = evaluate_levels(item, item.get("price"))
        rows.append(
            {
                "key": item["key"],
                "chain": item["chain"],
                "address": item["address"],
                "label": item.get("label") or "",
                "symbol": item.get("symbol") or "-",
                "price": item.get("price"),
                "liq": item.get("liq"),
                "ema9": _last_value(ema.get("9")),
                "ema21": _last_value(ema.get("21")),
                "rsi14": _last_value(rsi.get("14")),
                "nearest_level": verdict.get("nearest_level"),
                "nearest_distance_pct": verdict.get("nearest_distance_pct"),
                "level_status": verdict.get("status"),
            }
        )
    return rows


def render_report_text(rows: list[dict]) -> str:
    """Render report rows as an aligned terminal table."""
    if not rows:
        return "Watchlist is empty."
    header = (
        f"{'TOKEN':<16} {'CHAIN':<6} {'PRICE':>14} {'LIQ':>10} "
        f"{'EMA9':>12} {'EMA21':>12} {'RSI14':>7} {'LEVEL':<8} {'DIST':>9}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        token = str(row.get("symbol") or row.get("label") or row.get("address") or "-")[:16]
        rsi = row.get("rsi14")
        rsi_text = "-" if rsi is None else f"{rsi:.1f}"
        distance = row.get("nearest_distance_pct")
        dist_text = "-" if distance is None else f"{distance:+.2f}%"
        lines.append(
            f"{token:<16} {str(row.get('chain') or '-'):<6} {price(row.get('price')):>14} "
            f"{money(row.get('liq')):>10} {price(row.get('ema9')):>12} "
            f"{price(row.get('ema21')):>12} {rsi_text:>7} "
            f"{str(row.get('nearest_level') or '-'):<8} {dist_text:>9}"
        )
    return "\n".join(lines)

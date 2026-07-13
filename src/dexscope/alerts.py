"""One-shot read-only threshold checks for a user's own watchlist levels.

These helpers only compare public live prices with the user's own entry/SL/TP
numbers. They do not poll, send notifications, or produce trading recommendations.
"""

from __future__ import annotations

from .formatting import price
from .util import to_float
from .watchlist import LEVEL_FIELDS

NEAR_PCT = 2.0


def _distance_pct(current: float, level: float) -> float:
    return ((current - level) / level) * 100.0


def _is_crossed(name: str, current: float, level: float) -> bool:
    if name in {"entry", "sl"}:
        return current <= level
    return current >= level


def evaluate_levels(row: dict, live_price: float | None) -> dict:
    """Return a structured verdict for one token and current price."""
    current = to_float(live_price)
    levels = {
        name: level
        for name in LEVEL_FIELDS
        if (level := to_float(row.get(name))) is not None and level > 0
    }
    verdict: dict = {
        "key": row.get("key") or f"{row.get('chain', '')}:{row.get('address', '')}",
        "chain": row.get("chain") or "",
        "address": row.get("address") or "",
        "label": row.get("label") or "",
        "price": current,
        "status": "NO_PRICE" if levels else "NO_LEVELS",
        "hit": False,
        "nearest_level": None,
        "nearest_distance_pct": None,
        "levels": [],
    }
    if not levels:
        return verdict
    if current is None or current <= 0:
        verdict["status"] = "NO_PRICE"
        return verdict

    checks: list[dict] = []
    for name in LEVEL_FIELDS:
        level = levels.get(name)
        if level is None:
            continue
        distance = _distance_pct(current, level)
        checks.append(
            {
                "name": name,
                "value": level,
                "distance_pct": distance,
                "hit": _is_crossed(name, current, level),
            }
        )
    verdict["levels"] = checks
    hit_names = [item["name"] for item in checks if item["hit"]]
    verdict["hit"] = bool(hit_names)

    nearest = min(checks, key=lambda item: abs(item["distance_pct"]))
    verdict["nearest_level"] = nearest["name"]
    verdict["nearest_distance_pct"] = nearest["distance_pct"]

    if "sl" in hit_names:
        verdict["status"] = "BELOW_SL"
    elif "tp2" in hit_names:
        verdict["status"] = "ABOVE_TP2"
    elif "tp1" in hit_names:
        verdict["status"] = "ABOVE_TP1"
    elif "entry" in hit_names:
        verdict["status"] = "BELOW_ENTRY"
    elif abs(nearest["distance_pct"]) <= NEAR_PCT:
        verdict["status"] = f"NEAR_{nearest['name'].upper()}"
    else:
        ordered = sorted(levels.values())
        if current < ordered[0]:
            verdict["status"] = "BELOW_ALL"
        elif current > ordered[-1]:
            verdict["status"] = "ABOVE_ALL"
        else:
            verdict["status"] = "BETWEEN"
    return verdict


def build_alert_rows(
    watchlist: list[dict], live: dict[str, dict], *, only_hit: bool = False
) -> list[dict]:
    """Build alert verdicts from normalized watchlist rows and live DexScreener data."""
    rows: list[dict] = []
    for row in watchlist:
        if not any(to_float(row.get(name)) is not None for name in LEVEL_FIELDS):
            continue
        info = live.get(row["key"]) or {}
        verdict = evaluate_levels(row, to_float(info.get("price")))
        verdict["symbol"] = info.get("symbol") or row.get("label") or "-"
        verdict["url"] = info.get("url") or ""
        if only_hit and not verdict["hit"]:
            continue
        rows.append(verdict)
    return rows


def render_alert_text(rows: list[dict]) -> str:
    """Render alert verdicts as an aligned terminal table."""
    if not rows:
        return "No watchlist levels matched."
    header = f"{'TOKEN':<16} {'PRICE':>14} {'STATUS':<12} {'NEAREST':<8} {'DIST':>9}"
    lines = [header, "-" * len(header)]
    for row in rows:
        token = str(row.get("symbol") or row.get("label") or row.get("address") or "-")[:16]
        nearest = str(row.get("nearest_level") or "-")
        distance = row.get("nearest_distance_pct")
        dist_text = "-" if distance is None else f"{distance:+.2f}%"
        lines.append(
            f"{token:<16} {price(row.get('price')):>14} "
            f"{str(row.get('status') or '-'):<12} {nearest:<8} {dist_text:>9}"
        )
    return "\n".join(lines)

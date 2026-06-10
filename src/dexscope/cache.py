"""On-disk OHLCV cache so repeat page loads don't re-hit the providers.

One JSON file per (chain, timeframe, pool). A cache entry is "fresh" while it is younger
than ``ttl_sec``; stale entries are ignored (and overwritten on the next fetch).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .chains import norm_chain
from .util import parse_iso, read_json, utcnow, write_json

_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_cache_name(chain: str, pool: str, timeframe: str) -> str:
    """Filesystem-safe cache filename. Pool addresses can contain characters that are
    illegal in filenames on some platforms, so non-alphanumerics collapse to ``_``."""
    safe_pool = _UNSAFE.sub("_", pool or "")
    return f"{norm_chain(chain)}_{timeframe}_{safe_pool}.json"


def read_fresh(path: Path, ttl_sec: int, *, now: datetime | None = None) -> list[dict] | None:
    """Return cached candle rows if the file exists and is younger than ``ttl_sec``."""
    cached = read_json(path, {})
    if not isinstance(cached, dict):
        return None
    fetched_at = parse_iso(cached.get("fetched_at"))
    if not fetched_at:
        return None
    moment = now or utcnow()
    if (moment - fetched_at).total_seconds() >= ttl_sec:
        return None
    rows = cached.get("rows")
    return rows if isinstance(rows, list) and rows else None


def write_candles(path: Path, rows: list[dict], meta: dict[str, Any] | None = None) -> None:
    """Persist candle rows with a ``fetched_at`` stamp (and optional provenance meta)."""
    payload: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows": rows,
    }
    if meta:
        payload.update(meta)
    write_json(path, payload)

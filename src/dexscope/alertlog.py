"""Append-only JSONL history for the user's own watchlist level checks.

Records are written locally from data the ``alert`` command already computed:
public prices compared with the user's own entry/SL/TP numbers. Nothing is sent
anywhere and the timestamp is always supplied by the caller so the output stays
deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .util import to_float

RECORD_FIELDS = (
    "checked_at",
    "key",
    "chain",
    "address",
    "symbol",
    "price",
    "status",
    "hit",
    "nearest_level",
    "nearest_distance_pct",
    "levels_hit",
)


def alert_row_to_record(row: dict, *, checked_at: int) -> dict[str, Any]:
    """Reduce one alert verdict to a flat record with a stable key order."""
    levels = row.get("levels") or []
    return {
        "checked_at": checked_at,
        "key": row.get("key"),
        "chain": row.get("chain"),
        "address": row.get("address"),
        "symbol": row.get("symbol"),
        "price": to_float(row.get("price")),
        "status": row.get("status"),
        "hit": bool(row.get("hit")),
        "nearest_level": row.get("nearest_level"),
        "nearest_distance_pct": to_float(row.get("nearest_distance_pct")),
        "levels_hit": sorted(str(item.get("name")) for item in levels if item.get("hit")),
    }


def alert_rows_to_jsonl(rows: list[dict], *, checked_at: int) -> str:
    """Render alert verdicts as newline-terminated compact JSON objects."""
    if not rows:
        return ""
    lines = [
        json.dumps(alert_row_to_record(row, checked_at=checked_at), ensure_ascii=False)
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def append_jsonl(path: Path, payload: str) -> int:
    """Append ``payload`` to ``path`` and return how many lines were written.

    An empty payload is a no-op that leaves the filesystem untouched. The
    newline translation is disabled so a log written on Windows stays
    byte-identical to one written on Linux.
    """
    if not payload:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    return payload.count("\n")


def read_jsonl(path: Path) -> list[dict]:
    """Parse a JSONL log back into records, skipping blank lines.

    A missing file reads as an empty history rather than raising.
    """
    if not path.exists():
        return []
    records: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records

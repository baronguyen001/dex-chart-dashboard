"""Small pure helpers shared across the package (no I/O side effects beyond JSON files)."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def to_float(value: Any) -> float | None:
    """Coerce to a finite float or None (NaN/inf and unparseable -> None)."""
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def iso(dt: datetime | None) -> str | None:
    """UTC ISO-8601 with a trailing ``Z`` (or None)."""
    if not dt:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(value: Any) -> datetime | None:
    """Parse an ISO timestamp (``Z`` or offset) into a tz-aware UTC datetime, else None."""
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        out = datetime.fromisoformat(text)
    except ValueError:
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

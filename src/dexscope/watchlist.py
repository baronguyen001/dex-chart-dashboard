"""The watchlist: a plain JSON list of tokens you want to chart.

Each row is ``{chain, address, label?, note?, entry?, sl?, tp1?, tp2?}``. ``chain`` and
``address`` are required; the rest are optional. ``entry``/``sl``/``tp1``/``tp2`` are
drawn as horizontal level lines on the token chart. This file fully replaces the private
scan/position ingestion the dashboard was lifted from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .chains import DEX_CHAINS, norm_chain, token_key
from .util import read_json, to_float, write_json

LEVEL_FIELDS = ("entry", "sl", "tp1", "tp2")
TEXT_FIELDS = ("label", "note")


def _rows(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        raw = raw.get("tokens") or raw.get("watchlist") or []
    return [row for row in (raw or []) if isinstance(row, dict)]


def normalize_row(row: dict) -> dict | None:
    """Validate + coerce a single watchlist row, or return None if unusable."""
    chain = norm_chain(row.get("chain"))
    address = (row.get("address") or "").strip()  # case preserved (SOL base58 is case-sensitive)
    if not address or chain not in DEX_CHAINS:
        return None
    out: dict[str, Any] = {"chain": chain, "address": address, "key": token_key(chain, address)}
    for field in TEXT_FIELDS:
        value = row.get(field)
        if value:
            out[field] = str(value)
    for field in LEVEL_FIELDS:
        out[field] = to_float(row.get(field))
    return out


def load_watchlist(path: Path) -> list[dict]:
    """Read + validate the watchlist file, dropping malformed/duplicate rows."""
    rows: list[dict] = []
    seen: set[str] = set()
    for raw in _rows(read_json(path, [])):
        row = normalize_row(raw)
        if not row or row["key"] in seen:
            continue
        seen.add(row["key"])
        rows.append(row)
    return rows


def add_entry(path: Path, chain: str, address: str, **fields: Any) -> dict:
    """Append a token to the watchlist file (no-op fields are dropped). Idempotent on key."""
    candidate = normalize_row({"chain": chain, "address": address, **fields})
    if candidate is None:
        raise ValueError(f"unsupported chain or empty address: chain={chain!r} address={address!r}")
    kept: list[dict] = []
    for raw in _rows(read_json(path, [])):
        norm = normalize_row(raw)
        if norm is None or norm["key"] != candidate["key"]:
            kept.append(raw)
    stored: dict[str, Any] = {"chain": candidate["chain"], "address": candidate["address"]}
    for field in (*TEXT_FIELDS, *LEVEL_FIELDS):
        if candidate.get(field) is not None:
            stored[field] = candidate[field]
    kept.append(stored)
    write_json(path, kept)
    return candidate


def build_items(watchlist: list[dict], live: dict[str, dict]) -> list[dict]:
    """Join watchlist rows with live DexScreener price/liq into display items."""
    items: list[dict] = []
    for row in watchlist:
        info = live.get(row["key"]) or {}
        items.append(
            {
                **row,
                "symbol": info.get("symbol") or row.get("label") or "-",
                "label": row.get("label") or "",
                "note": row.get("note") or "",
                "price": to_float(info.get("price")),
                "liq": to_float(info.get("liq")),
                "url": info.get("url") or "",
                "pool": "",  # resolved lazily on the token chart page
            }
        )
    return items

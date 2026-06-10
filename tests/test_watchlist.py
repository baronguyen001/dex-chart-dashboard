from __future__ import annotations

import json

from dexscope.watchlist import add_entry, build_items, load_watchlist, normalize_row


def test_normalize_row_valid_and_invalid():
    ok = normalize_row({"chain": "Solana", "address": "ADDR", "entry": "1.5", "label": "X"})
    assert ok is not None
    assert ok["chain"] == "sol"
    assert ok["entry"] == 1.5
    assert ok["key"] == "sol:ADDR"
    assert normalize_row({"chain": "polygon", "address": "ADDR"}) is None  # unsupported chain
    assert normalize_row({"chain": "sol", "address": ""}) is None  # empty address


def test_load_watchlist_dedupes_and_filters(tmp_path):
    path = tmp_path / "w.json"
    path.write_text(
        json.dumps(
            [
                {"chain": "sol", "address": "A"},
                {"chain": "sol", "address": "A"},  # dup
                {"chain": "polygon", "address": "B"},  # unsupported
                {"chain": "eth", "address": "0xC"},
            ]
        ),
        encoding="utf-8",
    )
    rows = load_watchlist(path)
    assert [r["key"] for r in rows] == ["sol:A", "eth:0xC"]


def test_load_watchlist_accepts_tokens_wrapper(tmp_path):
    path = tmp_path / "w.json"
    path.write_text(json.dumps({"tokens": [{"chain": "sol", "address": "A"}]}), encoding="utf-8")
    assert len(load_watchlist(path)) == 1


def test_add_entry_appends_and_is_idempotent(tmp_path):
    path = tmp_path / "w.json"
    add_entry(path, "sol", "A", label="First", entry=1.0)
    add_entry(path, "sol", "A", label="Updated")  # same key -> replace, not duplicate
    rows = load_watchlist(path)
    assert len(rows) == 1
    assert rows[0]["label"] == "Updated"


def test_build_items_merges_live_prices():
    watchlist = [
        {
            "chain": "sol",
            "address": "A",
            "key": "sol:A",
            "label": "X",
            "entry": None,
            "sl": None,
            "tp1": None,
            "tp2": None,
        }
    ]
    live = {"sol:A": {"price": 1.23, "liq": 5000.0, "url": "u", "symbol": "XSYM"}}
    items = build_items(watchlist, live)
    assert items[0]["price"] == 1.23
    assert items[0]["symbol"] == "XSYM"
    assert items[0]["liq"] == 5000.0

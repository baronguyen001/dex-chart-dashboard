from __future__ import annotations

from datetime import timedelta

from dexscope.cache import read_fresh, safe_cache_name, write_candles
from dexscope.util import utcnow


def test_safe_cache_name_sanitizes_pool():
    name = safe_cache_name("Solana", "abc/def:ghi", "1h")
    assert name == "sol_1h_abc_def_ghi.json"
    assert "/" not in name and ":" not in name


def test_write_then_read_fresh(tmp_path):
    path = tmp_path / "c.json"
    rows = [{"ts": 0, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}]
    write_candles(path, rows, {"source": "test"})
    assert read_fresh(path, ttl_sec=900) == rows


def test_stale_cache_returns_none(tmp_path):
    path = tmp_path / "c.json"
    write_candles(path, [{"ts": 0, "close": 1.0}])
    future = utcnow() + timedelta(seconds=10_000)
    assert read_fresh(path, ttl_sec=900, now=future) is None


def test_missing_cache_returns_none(tmp_path):
    assert read_fresh(tmp_path / "nope.json", ttl_sec=900) is None

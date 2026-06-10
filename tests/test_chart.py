from __future__ import annotations

from dexscope.chart import build_chart_bundle, build_chart_frame, merge_candles


def _candles(n):
    return [
        {"ts": i * 3600, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}
        for i in range(n)
    ]


class _StubGecko:
    def __init__(self, by_tf):
        self.by_tf = by_tf

    def fetch(self, chain, pool, timeframe="1h"):
        return self.by_tf.get(timeframe, [])


def test_merge_candles_fills_missing_fields():
    a = [{"ts": 0, "open": 1.0, "high": None, "low": 0.5, "close": 1.2, "volume": None}]
    b = [{"ts": 0, "open": None, "high": 1.4, "low": None, "close": None, "volume": 9.0}]
    out = merge_candles(a, b)
    assert len(out) == 1
    assert out[0]["high"] == 1.4
    assert out[0]["volume"] == 9.0
    assert out[0]["open"] == 1.0


def test_build_chart_frame_level_lines_match_label_length():
    candles = _candles(5)
    frame = build_chart_frame(candles, {"entry": 1.0, "sl": 0.5, "tp1": None, "tp2": None}, "1h")
    assert frame["has_chart"] is True
    assert len(frame["labels"]) == 5
    assert frame["levels"]["entry"] == [1.0] * 5
    assert frame["levels"]["sl"] == [0.5] * 5
    assert frame["levels"]["tp1"] == []  # None level -> no line


def test_build_chart_bundle_selects_richest_readable_frame():
    gecko = _StubGecko({"1h": _candles(30), "5m": _candles(3)})
    item = {"chain": "sol", "address": "ADDR", "pool": "POOL", "entry": 1.0}
    bundle = build_chart_bundle(gecko, item)
    assert bundle["selected_timeframe"] == "1h"
    assert "1h" in bundle["timeframes"]
    assert any(s["timeframe"] == "5m" and s["available"] for s in bundle["timeframe_summary"])


def test_build_chart_bundle_no_pool_is_empty():
    gecko = _StubGecko({})
    bundle = build_chart_bundle(gecko, {"chain": "sol", "address": "ADDR", "pool": ""})
    assert bundle["has_chart"] is False
    assert bundle["available_timeframes"] == []

from __future__ import annotations

from dexscope.report import build_report_rows, render_report_text


def test_build_report_rows_joins_live_indicators_and_nearest_level():
    watchlist = [
        {
            "key": "sol:A",
            "chain": "sol",
            "address": "A",
            "label": "Alpha",
            "entry": 1.0,
            "sl": 0.8,
            "tp1": 1.5,
            "tp2": None,
        }
    ]
    live = {"sol:A": {"price": 1.2, "liq": 5000, "symbol": "AAA", "url": "https://dex/x"}}
    indicators = {
        "sol:A": {
            "ema": {"9": [None, 1.1, 1.2], "21": [None, None, 1.05]},
            "rsi": {"14": [None, 55.5]},
        }
    }
    rows = build_report_rows(watchlist, live, indicators)
    assert rows == [
        {
            "key": "sol:A",
            "chain": "sol",
            "address": "A",
            "label": "Alpha",
            "symbol": "AAA",
            "price": 1.2,
            "liq": 5000.0,
            "ema9": 1.2,
            "ema21": 1.05,
            "rsi14": 55.5,
            "nearest_level": "entry",
            "nearest_distance_pct": 19.999999999999996,
            "level_status": "BETWEEN",
        }
    ]


def test_render_report_text_formats_rows_and_empty_state():
    rows = [
        {
            "symbol": "AAA",
            "chain": "sol",
            "price": 1.2,
            "liq": 5000,
            "ema9": 1.1,
            "ema21": 1.0,
            "rsi14": 55.5,
            "nearest_level": "tp1",
            "nearest_distance_pct": -20.0,
        }
    ]
    text = render_report_text(rows)
    assert "TOKEN" in text
    assert "AAA" in text
    assert "tp1" in text
    assert "-20.00%" in text
    assert render_report_text([]) == "Watchlist is empty."

from __future__ import annotations

import json

from dexscope.exporter import CANDLE_COLUMNS, candles_to_csv, candles_to_json, indicator_columns

CANDLES = [
    {"ts": 1000, "open": "10.5", "high": 11, "low": "9.5", "close": 10.8, "volume": 100},
    {"ts": 2000, "open": None, "high": None, "low": "8", "close": None, "volume": 0},
]

BARE_CSV = "ts,open,high,low,close,volume\n1000,10.5,11.0,9.5,10.8,100.0\n2000,,,8.0,,0.0\n"

FULL_INDICATORS = {
    "ema": {"9": [1.1, 2.2], "21": [3.3, 4.4]},
    "rsi": {"14": [50.0, 60.0]},
    "macd": {"macd": [0.1, 0.2], "signal": [0.3, 0.4], "histogram": [0.5, 0.6]},
    "bollinger": {"middle": [100.0, 101.0], "upper": [105.0, 106.0], "lower": [95.0, 96.0]},
}


def test_indicator_columns_of_nothing_is_empty():
    assert indicator_columns(None) == []
    assert indicator_columns({}) == []
    assert indicator_columns({"ema": {}, "macd": {}, "bollinger": {}}) == []


def test_indicator_columns_order_is_stable():
    names = [name for name, _ in indicator_columns(FULL_INDICATORS)]
    assert names == [
        "ema_9",
        "ema_21",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_middle",
        "bb_upper",
        "bb_lower",
    ]


def test_indicator_columns_sorts_periods_numerically_not_lexically():
    names = [
        name for name, _ in indicator_columns({"ema": {"20": [1.0], "5": [2.0], "100": [3.0]}})
    ]
    assert names == ["ema_5", "ema_20", "ema_100"]


def test_indicator_columns_skips_non_numeric_periods():
    indicators = {"ema": {"9": [1.0], "badkey": [2.0], "21": [3.0]}, "rsi": {"not_int": [70.0]}}
    names = [name for name, _ in indicator_columns(indicators)]
    assert names == ["ema_9", "ema_21"]


def test_indicator_columns_keeps_zero_padded_period_values():
    columns = indicator_columns({"ema": {"09": [1.0, 2.0]}})
    assert columns == [("ema_9", [1.0, 2.0])]


def test_indicator_columns_skips_partial_fixed_key_overlays():
    names = [name for name, _ in indicator_columns({"macd": {"macd": [1.0]}})]
    assert names == ["macd"]


def test_csv_without_indicators_is_unchanged():
    assert candles_to_csv(CANDLES) == BARE_CSV
    assert candles_to_csv(CANDLES, indicators=None) == BARE_CSV
    assert candles_to_csv(CANDLES, indicators={}) == BARE_CSV


def test_csv_appends_indicator_columns():
    lines = candles_to_csv(CANDLES, indicators=FULL_INDICATORS).splitlines()
    assert lines[0] == (
        "ts,open,high,low,close,volume,ema_9,ema_21,rsi_14,"
        "macd,macd_signal,macd_hist,bb_middle,bb_upper,bb_lower"
    )
    assert lines[1] == "1000,10.5,11.0,9.5,10.8,100.0,1.1,3.3,50.0,0.1,0.3,0.5,100.0,105.0,95.0"
    assert lines[2] == "2000,,,8.0,,0.0,2.2,4.4,60.0,0.2,0.4,0.6,101.0,106.0,96.0"


def test_csv_pads_short_overlay_with_blank_cells():
    lines = candles_to_csv(CANDLES, indicators={"ema": {"9": [1.1]}}).splitlines()
    assert lines[1] == "1000,10.5,11.0,9.5,10.8,100.0,1.1"
    assert lines[2] == "2000,,,8.0,,0.0,"


def test_csv_ignores_overlay_values_beyond_the_candles():
    lines = candles_to_csv(CANDLES, indicators={"rsi": {"14": [70.0, 71.0, 72.0]}}).splitlines()
    assert len(lines) == 3
    assert lines[2] == "2000,,,8.0,,0.0,71.0"


def test_csv_of_no_candles_still_writes_the_header():
    assert candles_to_csv([]) == "ts,open,high,low,close,volume\n"
    header = candles_to_csv([], indicators={"ema": {"9": []}})
    assert header == "ts,open,high,low,close,volume,ema_9\n"


def test_json_without_indicators_is_unchanged():
    rows = json.loads(candles_to_json(CANDLES))
    assert list(rows[0]) == list(CANDLE_COLUMNS)
    assert rows[0] == {
        "ts": 1000,
        "open": 10.5,
        "high": 11.0,
        "low": 9.5,
        "close": 10.8,
        "volume": 100.0,
    }
    assert rows[1]["open"] is None
    assert candles_to_json(CANDLES, indicators={}) == candles_to_json(CANDLES)


def test_json_appends_indicator_keys_after_ohlcv():
    rows = json.loads(candles_to_json(CANDLES, indicators={"ema": {"9": [1.1, 2.2]}}))
    assert list(rows[0]) == [*CANDLE_COLUMNS, "ema_9"]
    assert rows[0]["ema_9"] == 1.1
    assert rows[1]["ema_9"] == 2.2


def test_json_pads_short_overlay_with_null():
    candles = [{"ts": index, "close": index} for index in range(3)]
    rows = json.loads(candles_to_json(candles, indicators={"ema": {"5": [10.0, 20.0]}}))
    assert [row["ema_5"] for row in rows] == [10.0, 20.0, None]


def test_json_of_no_candles_is_an_empty_array():
    assert candles_to_json([]) == "[]"
    assert candles_to_json([], indicators={"ema": {"9": []}}) == "[]"

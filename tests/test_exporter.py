from __future__ import annotations

import json

from dexscope.exporter import candles_to_csv, candles_to_json


def _candles() -> list[dict]:
    return [
        {"ts": "0", "open": "1", "high": 2, "low": 0.5, "close": 1.5, "volume": 10},
        {"ts": 60, "open": 1.5, "high": 2.5, "low": 1.25, "close": "2", "volume": None},
    ]


def test_candles_to_csv_uses_stable_columns():
    text = candles_to_csv(_candles())
    assert text.splitlines()[0] == "ts,open,high,low,close,volume"
    assert text.splitlines()[1] == "0,1.0,2.0,0.5,1.5,10.0"
    assert text.splitlines()[2] == "60,1.5,2.5,1.25,2.0,"


def test_candles_to_json_uses_stable_keys():
    rows = json.loads(candles_to_json(_candles()))
    assert list(rows[0]) == ["ts", "open", "high", "low", "close", "volume"]
    assert rows[0]["ts"] == 0
    assert rows[1]["volume"] is None

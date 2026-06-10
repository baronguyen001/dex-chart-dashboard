from __future__ import annotations

from dexscope.gecko import resample_candles


def _row(ts, o, h, low, c, v):
    return {"ts": ts, "open": o, "high": h, "low": low, "close": c, "volume": v}


def test_resample_1h_to_2h():
    rows = [
        _row(0, 0.80, 0.92, 0.79, 0.90, 65000.0),
        _row(3600, 0.90, 1.00, 0.88, 0.98, 73000.0),
        _row(7200, 0.98, 1.08, 0.95, 1.05, 80000.0),
        _row(10800, 1.05, 1.12, 1.00, 1.10, 47000.0),
        _row(14400, 1.10, 1.25, 1.05, 1.20, 61000.0),
        _row(18000, 1.20, 1.35, 1.18, 1.30, 52000.0),
    ]
    out = resample_candles(rows, 7200)
    assert [c["ts"] for c in out] == [0, 7200, 14400]

    first = out[0]
    assert first["open"] == 0.80  # first open in bucket
    assert first["close"] == 0.98  # last close in bucket
    assert first["high"] == 1.00  # max high
    assert first["low"] == 0.79  # min low
    assert first["volume"] == 65000.0 + 73000.0


def test_resample_15m_to_30m():
    rows = [
        _row(0, 1, 2, 0.5, 1.5, 10),
        _row(900, 1.5, 2.5, 1.4, 2.0, 20),
        _row(1800, 2.0, 2.2, 1.9, 2.1, 5),
        _row(2700, 2.1, 3.0, 2.0, 2.8, 7),
    ]
    out = resample_candles(rows, 1800)
    assert [c["ts"] for c in out] == [0, 1800]
    assert out[0]["high"] == 2.5
    assert out[0]["low"] == 0.5
    assert out[0]["close"] == 2.0
    assert out[1]["volume"] == 12


def test_resample_handles_unordered_input():
    rows = [
        _row(3600, 0.90, 1.00, 0.88, 0.98, 1),
        _row(0, 0.80, 0.92, 0.79, 0.90, 1),
    ]
    out = resample_candles(rows, 7200)
    assert len(out) == 1
    assert out[0]["open"] == 0.80  # earliest ts is the open even if input is unsorted
    assert out[0]["close"] == 0.98

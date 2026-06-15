from __future__ import annotations

import pytest

from dexscope.indicators import build_indicators, ema_values, rsi_values


def test_ema_values_are_deterministic():
    closes = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0]
    assert ema_values(closes, 3) == [10.0, 11.0, 11.0, 12.0, 12.0, 13.0, 13.0]


def test_rsi_values_are_deterministic():
    closes = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0]
    assert rsi_values(closes, 3) == [
        None,
        None,
        None,
        80.0,
        pytest.approx(61.5384615385),
        pytest.approx(77.2727272727),
        pytest.approx(59.1304347826),
    ]


def test_build_indicators_aligns_to_candles():
    candles = [{"close": value} for value in [10.0, 12.0, 11.0, 13.0]]
    out = build_indicators(candles, ema_periods=(3,), rsi_period=3)
    assert out["ema"]["3"] == [10.0, 11.0, 11.0, 12.0]
    assert out["rsi"]["3"] == [None, None, None, 80.0]

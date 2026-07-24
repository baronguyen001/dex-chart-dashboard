from __future__ import annotations

import math

import pytest

from dexscope.indicators import bollinger_values, build_indicators, ema_values, macd_values


def test_macd_output_lengths_match_input():
    values: list[float | None] = [1.0, 2.0, 3.0, None, 5.0]
    out = macd_values(values, fast=2, slow=3, signal=2)
    assert len(out["macd"]) == len(values)
    assert len(out["signal"]) == len(values)
    assert len(out["histogram"]) == len(values)


def test_macd_rejects_fast_not_shorter_than_slow():
    with pytest.raises(ValueError, match="shorter than the slow period"):
        macd_values([1.0, 2.0], fast=5, slow=5)
    with pytest.raises(ValueError, match="shorter than the slow period"):
        macd_values([1.0, 2.0], fast=6, slow=5)


def test_macd_rejects_non_positive_periods():
    with pytest.raises(ValueError, match="MACD periods must be positive"):
        macd_values([1.0], fast=0, slow=1, signal=1)
    with pytest.raises(ValueError, match="MACD periods must be positive"):
        macd_values([1.0], fast=1, slow=0, signal=1)
    with pytest.raises(ValueError, match="MACD periods must be positive"):
        macd_values([1.0], fast=1, slow=2, signal=0)


def test_macd_flat_series_has_no_divergence():
    out = macd_values([10.0] * 8, fast=2, slow=3, signal=2)
    assert out["macd"] == [0.0] * 8
    assert out["signal"] == [0.0] * 8
    assert out["histogram"] == [0.0] * 8


def test_macd_histogram_is_line_minus_signal():
    out = macd_values([10.0, 11.0, 12.0, 13.0, 14.0, 15.0], fast=3, slow=4, signal=2)
    for line, smoothed, bar in zip(out["macd"], out["signal"], out["histogram"], strict=True):
        if line is None or smoothed is None:
            assert bar is None
        else:
            assert bar == pytest.approx(line - smoothed)


def test_macd_signal_is_ema_of_macd_line():
    out = macd_values([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0], fast=3, slow=5, signal=3)
    expected = ema_values(out["macd"], 3)
    for got, want in zip(out["signal"], expected, strict=True):
        if want is None:
            assert got is None
        else:
            assert got == pytest.approx(want)


def test_macd_gap_propagates_to_every_series():
    out = macd_values([10.0, None, 12.0, 13.0], fast=2, slow=4, signal=2)
    assert out["macd"][1] is None
    assert out["signal"][1] is None
    assert out["histogram"][1] is None


def test_bollinger_output_lengths_match_input():
    values: list[float | None] = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = bollinger_values(values, period=3)
    assert len(out["middle"]) == len(values)
    assert len(out["upper"]) == len(values)
    assert len(out["lower"]) == len(values)


def test_bollinger_rejects_non_positive_period():
    with pytest.raises(ValueError, match="Bollinger period must be positive"):
        bollinger_values([1.0], period=0)
    with pytest.raises(ValueError, match="Bollinger period must be positive"):
        bollinger_values([1.0], period=-1)


def test_bollinger_rejects_negative_num_std():
    with pytest.raises(ValueError, match="num_std must be non-negative"):
        bollinger_values([1.0], period=2, num_std=-0.1)


def test_bollinger_flat_series_collapses_bands():
    out = bollinger_values([5.0] * 6, period=3)
    assert out["middle"][:2] == [None, None]
    for index in range(2, 6):
        assert out["middle"][index] == 5.0
        assert out["upper"][index] == 5.0
        assert out["lower"][index] == 5.0


def test_bollinger_ramp_matches_population_stdev():
    out = bollinger_values([2.0, 4.0, 6.0, 8.0], period=3, num_std=2.0)
    deviation = math.sqrt(8 / 3)
    assert out["middle"][0] is None
    assert out["middle"][1] is None
    assert out["middle"][2] == pytest.approx(4.0)
    assert out["upper"][2] == pytest.approx(4.0 + (2 * deviation))
    assert out["lower"][2] == pytest.approx(4.0 - (2 * deviation))
    assert out["middle"][3] == pytest.approx(6.0)
    assert out["upper"][3] == pytest.approx(6.0 + (2 * deviation))
    assert out["lower"][3] == pytest.approx(6.0 - (2 * deviation))


def test_bollinger_gap_resets_the_window():
    out = bollinger_values([1.0, 2.0, 3.0, None, 4.0, 5.0, 6.0], period=2)
    assert out["middle"][0] is None
    assert out["middle"][1] == pytest.approx(1.5)
    assert out["middle"][2] == pytest.approx(2.5)
    assert out["middle"][3] is None
    assert out["upper"][3] is None
    assert out["lower"][3] is None
    # The window restarts after the gap, so index 4 cannot be complete yet.
    assert out["middle"][4] is None
    assert out["middle"][5] == pytest.approx(4.5)
    assert out["middle"][6] == pytest.approx(5.5)


def test_bollinger_period_longer_than_series_is_all_none():
    out = bollinger_values([1.0, 2.0, 3.0], period=5)
    assert out["middle"] == [None, None, None]
    assert out["upper"] == [None, None, None]
    assert out["lower"] == [None, None, None]


def test_bollinger_period_one_tracks_each_close():
    out = bollinger_values([3.0, 4.0, None, 5.0], period=1, num_std=2.0)
    assert out["middle"] == [3.0, 4.0, None, 5.0]
    assert out["upper"] == [3.0, 4.0, None, 5.0]
    assert out["lower"] == [3.0, 4.0, None, 5.0]


def test_build_indicators_keeps_macd_and_bollinger_opt_in():
    candles = [{"close": value} for value in range(1, 10)]
    out = build_indicators(candles)
    assert out["macd"] == {}
    assert out["bollinger"] == {}
    assert set(out["ema"]) == {"9", "21"}
    assert set(out["rsi"]) == {"14"}


def test_build_indicators_enables_macd_and_bollinger_on_request():
    candles = [{"close": value} for value in range(1, 30)]
    out = build_indicators(
        candles,
        ema_periods=(5, 10),
        rsi_period=7,
        macd=(3, 6, 2),
        bollinger=(5, 1.5),
    )
    assert set(out["macd"]) == {"macd", "signal", "histogram"}
    assert set(out["bollinger"]) == {"middle", "upper", "lower"}
    assert set(out["ema"]) == {"5", "10"}
    assert set(out["rsi"]) == {"7"}
    for series in out["macd"].values():
        assert len(series) == len(candles)
    for series in out["bollinger"].values():
        assert len(series) == len(candles)


def test_build_indicators_propagates_period_errors():
    candles = [{"close": 1.0}]
    with pytest.raises(ValueError, match="shorter than the slow period"):
        build_indicators(candles, macd=(10, 5, 2))
    with pytest.raises(ValueError, match="Bollinger period must be positive"):
        build_indicators(candles, bollinger=(0, 2.0))

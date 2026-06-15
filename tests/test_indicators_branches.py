from __future__ import annotations

import pytest

from dexscope.indicators import ema_values, rsi_values


def test_ema_rejects_nonpositive_period():
    with pytest.raises(ValueError):
        ema_values([1.0, 2.0], 0)
    with pytest.raises(ValueError):
        ema_values([1.0, 2.0], -3)


def test_ema_passes_through_gaps():
    # a None close keeps the slot None and does not advance the EMA state
    assert ema_values([10.0, None, 12.0], 3) == [10.0, None, 11.0]


def test_rsi_rejects_nonpositive_period():
    with pytest.raises(ValueError):
        rsi_values([1.0, 2.0], 0)


def test_rsi_resets_after_gap():
    # the None mid-series resets the running averages; every slot is None here
    out = rsi_values([10.0, 11.0, None, 12.0, 13.0], 2)
    assert out == [None, None, None, None, None]
    assert len(out) == 5

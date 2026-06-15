from __future__ import annotations

import pytest

from conftest import load_fixture
from dexscope.gecko import parse_ohlcv_list
from dexscope.snapshot import export_snapshot


def test_export_snapshot_writes_png_when_viz_extra_is_installed(tmp_path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")

    fixture = load_fixture("gecko_ohlcv_1h.json")
    candles = parse_ohlcv_list(fixture["data"]["attributes"]["ohlcv_list"])
    out = tmp_path / "chart.png"

    export_snapshot(candles, out, title="EXMPL", timeframe="1h", ema_periods=(3,), rsi_period=3)

    assert out.exists()
    assert out.stat().st_size > 0

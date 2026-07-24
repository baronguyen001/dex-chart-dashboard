from __future__ import annotations

import json

from dexscope.alertlog import read_jsonl
from dexscope.cli import main


def _stub_market(monkeypatch, candles):
    from dexscope.dexscreener import DexScreenerClient
    from dexscope.gecko import GeckoClient

    monkeypatch.setattr(DexScreenerClient, "resolve_pool", lambda self, c, a: {"pool": "POOL"})
    monkeypatch.setattr(GeckoClient, "fetch", lambda self, c, p, timeframe="1h": candles)


def test_cli_alert_appends_a_jsonl_history_entry(tmp_path, monkeypatch, capsys):
    from dexscope.dexscreener import DexScreenerClient

    watchlist = tmp_path / "watchlist.json"
    watchlist.write_text(
        json.dumps([{"chain": "sol", "address": "A", "label": "AAA", "tp1": 1.1}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        DexScreenerClient,
        "live_prices",
        lambda self, tokens: {"sol:A": {"price": 1.2, "symbol": "AAA"}},
    )
    log = tmp_path / "history" / "alerts.jsonl"

    argv = ["alert", "--watchlist", str(watchlist), "--jsonl-out", str(log)]
    assert main(argv) == 0
    assert "Appended 1 row(s)" in capsys.readouterr().out

    # A second run appends rather than replacing, which is the point of a history log.
    assert main(argv) == 0
    capsys.readouterr()

    records = read_jsonl(log)
    assert len(records) == 2
    assert records[0]["status"] == "ABOVE_TP1"
    assert records[0]["levels_hit"] == ["tp1"]
    assert records[0]["checked_at"] > 0


def test_cli_export_without_indicators_has_only_ohlcv_columns(tmp_path, monkeypatch, capsys):
    candles = [{"ts": 0, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}]
    _stub_market(monkeypatch, candles)

    assert main(["export", "sol", "A"]) == 0
    header = capsys.readouterr().out.splitlines()[0]
    assert header == "ts,open,high,low,close,volume"


def test_cli_export_with_indicators_appends_overlay_columns(tmp_path, monkeypatch, capsys):
    candles = [
        {"ts": i * 3600, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.0 + i, "volume": 10}
        for i in range(30)
    ]
    _stub_market(monkeypatch, candles)

    out = tmp_path / "candles.csv"
    assert main(["export", "sol", "A", "--indicators", "--out", str(out)]) == 0
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert header == (
        "ts,open,high,low,close,volume,ema_9,ema_21,rsi_14,"
        "macd,macd_signal,macd_hist,bb_middle,bb_upper,bb_lower"
    )


def test_cli_export_indicators_honours_custom_periods(tmp_path, monkeypatch, capsys):
    candles = [
        {"ts": i * 3600, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.0 + i, "volume": 10}
        for i in range(30)
    ]
    _stub_market(monkeypatch, candles)

    argv = ["export", "sol", "A", "--indicators", "--format", "json", "--ema", "5", "--rsi", "7"]
    assert main(argv) == 0
    rows = json.loads(capsys.readouterr().out)
    assert "ema_5" in rows[0]
    assert "ema_9" not in rows[0]
    assert "rsi_7" in rows[0]
    assert rows[-1]["macd"] is not None

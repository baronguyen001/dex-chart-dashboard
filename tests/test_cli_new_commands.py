from __future__ import annotations

import json

from dexscope.cli import main


def test_cli_alert_json_uses_watchlist_and_stubbed_live_prices(tmp_path, monkeypatch, capsys):
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

    assert main(["alert", "--watchlist", str(watchlist), "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["status"] == "ABOVE_TP1"


def test_cli_export_writes_csv_and_prints_json(tmp_path, monkeypatch, capsys):
    from dexscope.dexscreener import DexScreenerClient
    from dexscope.gecko import GeckoClient

    candles = [{"ts": 0, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}]
    monkeypatch.setattr(DexScreenerClient, "resolve_pool", lambda self, c, a: {"pool": "POOL"})
    monkeypatch.setattr(GeckoClient, "fetch", lambda self, c, p, timeframe="1h": candles)

    out = tmp_path / "candles.csv"
    assert main(["export", "sol", "A", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").splitlines()[0] == "ts,open,high,low,close,volume"

    assert main(["export", "sol", "A", "--format", "json"]) == 0
    printed = capsys.readouterr().out
    assert '"close": 1.5' in printed


def test_cli_report_json_uses_stubbed_clients(tmp_path, monkeypatch, capsys):
    from dexscope.dexscreener import DexScreenerClient
    from dexscope.gecko import GeckoClient

    watchlist = tmp_path / "watchlist.json"
    watchlist.write_text(
        json.dumps([{"chain": "sol", "address": "A", "label": "AAA", "entry": 1.0}]),
        encoding="utf-8",
    )
    candles = [
        {"ts": i * 3600, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.0 + i, "volume": 10}
        for i in range(25)
    ]
    monkeypatch.setattr(
        DexScreenerClient,
        "resolve_pool",
        lambda self, c, a: {"pool": "POOL", "price": 2.0, "liq": 5000, "symbol": "AAA"},
    )
    monkeypatch.setattr(GeckoClient, "fetch", lambda self, c, p, timeframe="1h": candles)

    assert main(["report", "--watchlist", str(watchlist), "--format", "json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["symbol"] == "AAA"
    assert rows[0]["ema9"] is not None
    assert rows[0]["rsi14"] == 100.0

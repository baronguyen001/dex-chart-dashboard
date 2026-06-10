from __future__ import annotations

import json

from dexscope.config import Settings
from dexscope.web import create_app


def _settings(tmp_path, watchlist):
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps(watchlist), encoding="utf-8")
    return Settings(
        watchlist_path=path,
        cache_dir=tmp_path / "cache",
        live_cache_path=tmp_path / "live.json",
        rate_min_interval=0.0,
    )


def test_health_and_index(tmp_path):
    settings = _settings(tmp_path, [{"chain": "sol", "address": "ADDR1", "label": "EXMPL"}])
    client = create_app(settings).test_client()

    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.get_json()
    assert body["ok"] is True
    assert body["items"] == 1

    index = client.get("/")
    assert index.status_code == 200
    assert b"EXMPL" in index.data


def test_index_empty_watchlist(tmp_path):
    settings = _settings(tmp_path, [])
    client = create_app(settings).test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"watchlist is empty" in resp.data


def test_token_route_renders_chart(tmp_path, monkeypatch):
    from dexscope.dexscreener import DexScreenerClient
    from dexscope.gecko import GeckoClient

    monkeypatch.setattr(
        DexScreenerClient,
        "resolve_pool",
        lambda self, c, a: {
            "pool": "POOL",
            "url": "https://dex/x",
            "price": 1.3,
            "symbol": "EXMPL",
        },
    )
    candles = [
        {"ts": i * 3600, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0}
        for i in range(25)
    ]
    monkeypatch.setattr(
        GeckoClient,
        "fetch",
        lambda self, c, p, timeframe="1h": candles if timeframe == "1h" else [],
    )

    settings = _settings(tmp_path, [{"chain": "sol", "address": "ADDR1", "label": "EXMPL"}])
    client = create_app(settings).test_client()
    resp = client.get("/token/sol/ADDR1")
    assert resp.status_code == 200
    assert b"token-chart" in resp.data
    assert b"token-chart-data" in resp.data


def test_token_route_404_when_no_pool(tmp_path, monkeypatch):
    from dexscope.dexscreener import DexScreenerClient

    monkeypatch.setattr(DexScreenerClient, "resolve_pool", lambda self, c, a: {})
    settings = _settings(tmp_path, [])
    client = create_app(settings).test_client()
    assert client.get("/token/sol/UNKNOWN").status_code == 404

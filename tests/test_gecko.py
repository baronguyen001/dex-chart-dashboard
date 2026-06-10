from __future__ import annotations

from conftest import FakeResponse, client_factory_for, load_fixture
from dexscope.config import Settings
from dexscope.gecko import GeckoClient, parse_ohlcv_list
from dexscope.ratelimit import RateLimiter


def _settings(tmp_path):
    return Settings(cache_dir=tmp_path / "cache", rate_min_interval=0.0)


def test_parse_ohlcv_list_sorts_ascending():
    fixture = load_fixture("gecko_ohlcv_1h.json")
    rows = parse_ohlcv_list(fixture["data"]["attributes"]["ohlcv_list"])
    assert len(rows) == 6
    assert [r["ts"] for r in rows] == [0, 3600, 7200, 10800, 14400, 18000]
    assert rows[0]["open"] == 0.80
    assert rows[-1]["close"] == 1.30


def test_fetch_native_parses_and_caches(tmp_path):
    fixture = load_fixture("gecko_ohlcv_1h.json")
    calls = {"n": 0}

    def handler(url, params):
        calls["n"] += 1
        return FakeResponse(200, fixture)

    client = GeckoClient(
        _settings(tmp_path), RateLimiter(0.0), client_factory=client_factory_for(handler)
    )
    rows = client.fetch_native("sol", "POOL", "1h", "hour", 1, 240)
    assert len(rows) == 6
    # second call is served from disk cache -> no extra network hit
    again = client.fetch_native("sol", "POOL", "1h", "hour", 1, 240)
    assert again == rows
    assert calls["n"] == 1


def test_fetch_2h_is_resampled_from_1h(tmp_path):
    fixture = load_fixture("gecko_ohlcv_1h.json")
    client = GeckoClient(
        _settings(tmp_path),
        RateLimiter(0.0),
        client_factory=client_factory_for(lambda u, p: FakeResponse(200, fixture)),
    )
    rows = client.fetch("sol", "POOL", "2h")
    assert [r["ts"] for r in rows] == [0, 7200, 14400]


def test_fetch_backs_off_on_429(tmp_path):
    fixture = load_fixture("gecko_ohlcv_1h.json")
    seq = [FakeResponse(429, None, {}), FakeResponse(200, fixture)]
    sleeps: list[float] = []

    def handler(url, params):
        return seq.pop(0)

    client = GeckoClient(
        _settings(tmp_path),
        RateLimiter(0.0),
        client_factory=client_factory_for(handler),
        sleep=sleeps.append,
    )
    rows = client.fetch_native("sol", "POOL", "1h", "hour", 1, 240)
    assert len(rows) == 6
    assert sleeps == [6.0]  # first backoff step, since no Retry-After header


def test_fetch_unknown_chain_returns_empty(tmp_path):
    client = GeckoClient(_settings(tmp_path), RateLimiter(0.0))
    assert client.fetch("polygon", "POOL", "1h") == []

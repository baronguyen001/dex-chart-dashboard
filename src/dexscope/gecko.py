"""GeckoTerminal OHLCV client + local resampling for non-native timeframes.

``GeckoClient.fetch`` is the single entry point the rest of the app uses. For native
frames it hits GeckoTerminal directly (throttled, cached, with 429 backoff); for 30m/2h
it fetches the cached base frame (15m/1h) and resamples it with :func:`resample_candles`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from .cache import read_fresh, safe_cache_name, write_candles
from .chains import GECKO_CHAINS, norm_chain
from .config import GECKO_BASE, Settings
from .models import TIMEFRAME_SPECS
from .ratelimit import BACKOFFS, RateLimiter
from .util import to_float

ClientFactory = Callable[..., httpx.Client]


def resample_candles(rows: list[dict], period_sec: int) -> list[dict]:
    """Aggregate finer candles into fixed-width ``period_sec`` buckets.

    Used for 30m (from 15m) and 2h (from 1h), which GeckoTerminal does not serve
    natively. open=first, high=max, low=min, close=last (rows must be processed
    ascending by ts), volume=sum.
    """
    buckets: dict[int, dict] = {}
    for row in sorted(rows, key=lambda r: int(r["ts"])):
        bucket = (int(row["ts"]) // period_sec) * period_sec
        high, low, close = row.get("high"), row.get("low"), row.get("close")
        vol = row.get("volume")
        agg = buckets.get(bucket)
        if agg is None:
            buckets[bucket] = {
                "ts": bucket,
                "open": row.get("open"),
                "high": high,
                "low": low,
                "close": close,
                "volume": vol or 0.0,
            }
            continue
        if high is not None:
            agg["high"] = high if agg["high"] is None else max(agg["high"], high)
        if low is not None:
            agg["low"] = low if agg["low"] is None else min(agg["low"], low)
        if close is not None:
            agg["close"] = close  # ascending order -> last close wins
        agg["volume"] = (agg["volume"] or 0.0) + (vol or 0.0)
    return sorted(buckets.values(), key=lambda r: r["ts"])


def parse_ohlcv_list(raw: Any) -> list[dict]:
    """Turn GeckoTerminal's ``[[ts, o, h, l, c, v], ...]`` payload into candle dicts."""
    rows: list[dict] = []
    for row in raw or []:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        rows.append(
            {
                "ts": int(row[0]),
                "open": to_float(row[1]),
                "high": to_float(row[2]),
                "low": to_float(row[3]),
                "close": to_float(row[4]),
                "volume": to_float(row[5]) if len(row) > 5 else None,
            }
        )
    return sorted(
        [r for r in rows if r.get("ts") is not None and r.get("close") is not None],
        key=lambda r: r["ts"],
    )


class GeckoClient:
    def __init__(
        self,
        settings: Settings,
        limiter: RateLimiter,
        *,
        client_factory: ClientFactory = httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.limiter = limiter
        self._client_factory = client_factory
        self._sleep = sleep

    # -- internal --------------------------------------------------------------
    def _cache_path(self, chain: str, pool: str, timeframe: str):
        return self.settings.cache_dir / safe_cache_name(chain, pool, timeframe)

    def _get(self, client: httpx.Client, url: str, params: dict) -> httpx.Response:
        """Single throttled GET with bounded 429 backoff."""
        attempt = 0
        while True:
            self.limiter.wait()
            response = client.get(url, params=params)
            if response.status_code == 429 and attempt < len(BACKOFFS):
                retry_after = to_float(response.headers.get("Retry-After"))
                self._sleep(retry_after if retry_after and retry_after > 0 else BACKOFFS[attempt])
                attempt += 1
                continue
            return response

    # -- public ----------------------------------------------------------------
    def fetch_native(
        self, chain: str, pool: str, timeframe: str, resolution: str, aggregate: int, limit: int
    ) -> list[dict]:
        chain = norm_chain(chain)
        gecko_chain = GECKO_CHAINS.get(chain)
        if not gecko_chain or not pool:
            return []

        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(chain, pool, timeframe)
        cached = read_fresh(cache_path, self.settings.cache_ttl_sec)
        if cached is not None:
            return cached

        url = f"{GECKO_BASE}/networks/{gecko_chain}/pools/{pool}/ohlcv/{resolution}"
        params = {"aggregate": aggregate, "limit": limit}
        rows: list[dict] = []
        try:
            with self._client_factory(
                headers={"User-Agent": self.settings.user_agent}, timeout=20
            ) as client:
                response = self._get(client, url, params)
                if response.status_code == 200:
                    raw = (
                        (response.json().get("data") or {})
                        .get("attributes", {})
                        .get("ohlcv_list", [])
                    )
                    rows = parse_ohlcv_list(raw)
        except (httpx.HTTPError, ValueError):
            rows = []

        if rows:
            write_candles(
                cache_path,
                rows,
                {"source": url, "resolution": resolution, "aggregate": aggregate},
            )
        return rows

    def fetch(self, chain: str, pool: str, timeframe: str = "1h") -> list[dict]:
        """OHLC for a UI timeframe label. Native frames hit Gecko; 30m/2h are resampled
        from a cached base frame."""
        spec = TIMEFRAME_SPECS.get(timeframe) or {
            "resolution": timeframe,
            "aggregate": 1,
            "limit": 500,
        }
        if "derive_from" not in spec:
            return self.fetch_native(
                chain, pool, timeframe, spec["resolution"], spec["aggregate"], spec["limit"]
            )

        chain = norm_chain(chain)
        if not pool or chain not in GECKO_CHAINS:
            return []
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(chain, pool, timeframe)
        cached = read_fresh(cache_path, self.settings.cache_ttl_sec)
        if cached is not None:
            return cached

        base_rows = self.fetch(chain, pool, spec["derive_from"])  # uses its own cache
        rows = resample_candles(base_rows, spec["period_sec"])
        if rows:
            write_candles(
                cache_path,
                rows,
                {"derived_from": spec["derive_from"], "period_sec": spec["period_sec"]},
            )
        return rows

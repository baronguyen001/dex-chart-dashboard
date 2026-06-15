"""Quickstart: resample 1h candles into 2h locally (offline), then optionally do a live fetch.

    python examples/quickstart.py                 # offline: resample a built-in 1h sample to 2h
    python examples/quickstart.py --live sol <token-address>   # live: resolve pool + fetch 1h OHLC

The offline path needs no network and is what CI / a first run exercises.
"""

from __future__ import annotations

import argparse

from dexscope.config import load_settings
from dexscope.dexscreener import DexScreenerClient
from dexscope.gecko import GeckoClient, resample_candles
from dexscope.indicators import ema_values
from dexscope.ratelimit import RateLimiter

# A tiny built-in 1h OHLCV sample (ts, open, high, low, close, volume) — purely illustrative.
SAMPLE_1H = [
    {"ts": 0, "open": 0.80, "high": 0.92, "low": 0.79, "close": 0.90, "volume": 65000.0},
    {"ts": 3600, "open": 0.90, "high": 1.00, "low": 0.88, "close": 0.98, "volume": 73000.0},
    {"ts": 7200, "open": 0.98, "high": 1.08, "low": 0.95, "close": 1.05, "volume": 80000.0},
    {"ts": 10800, "open": 1.05, "high": 1.12, "low": 1.00, "close": 1.10, "volume": 47000.0},
]


def offline_demo() -> None:
    print(f"1h candles in : {len(SAMPLE_1H)}")
    two_hour = resample_candles(SAMPLE_1H, period_sec=7200)
    print(f"2h candles out: {len(two_hour)}  (resampled locally; GeckoTerminal has no native 2h)")
    for c in two_hour:
        print(
            f"  ts={c['ts']:>6}  O {c['open']:.2f}  H {c['high']:.2f}  "
            f"L {c['low']:.2f}  C {c['close']:.2f}"
        )
    closes = [c["close"] for c in SAMPLE_1H]
    print(f"EMA(3) closes : {[round(v, 4) for v in ema_values(closes, 3) if v is not None]}")


def live_demo(chain: str, address: str) -> int:
    settings = load_settings()
    dex = DexScreenerClient(settings)
    info = dex.resolve_pool(chain, address)
    if not info.get("pool"):
        print(f"No pool found for {chain}:{address}")
        return 1
    print(f"Resolved {info.get('symbol') or '?'} pool {info['pool']} @ {info.get('price')}")
    gecko = GeckoClient(settings, RateLimiter(settings.rate_min_interval))
    rows = gecko.fetch(chain, info["pool"], "1h")
    print(f"Fetched {len(rows)} x 1h candles. Last close: {rows[-1]['close'] if rows else 'n/a'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", nargs=2, metavar=("CHAIN", "ADDRESS"))
    args = parser.parse_args()
    if args.live:
        return live_demo(args.live[0], args.live[1])
    offline_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

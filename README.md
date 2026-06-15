<div align="center">

# dex-chart-dashboard

### Self-hosted DEX token charts — multi-timeframe candlesticks from free APIs, no keys.

[![CI](https://github.com/baronguyen001/dex-chart-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/baronguyen001/dex-chart-dashboard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

A tiny Flask dashboard that charts any token on Ethereum / BSC / Base / Solana with
**1m → 1d candlesticks** pulled from **GeckoTerminal** and live price/liquidity from
**DexScreener** — both **keyless**. It resamples the **30m and 2h** frames locally
(GeckoTerminal serves neither), throttles + caches requests so a cold load never trips
the free-tier rate limit, and draws your own entry / SL / TP lines on the chart.
v0.2.0 adds optional EMA/RSI overlays, a watchlist compare view, and PNG chart snapshots
for README or launch posts.

</div>

---

## Why

Most "DEX chart" tools either need a paid data key, or hammer the free API until it
429s and the page half-loads. This is the boring engine that fixes both:

- **30m & 2h, which GeckoTerminal doesn't serve**, are resampled client-side from 15m / 1h.
- A **process-wide throttle (~27 req/min) + 429 backoff + 15-minute disk cache** keeps an
  8-timeframe page under the free tier no matter how many tabs you open.
- **No API keys.** GeckoTerminal (OHLCV) and DexScreener (price/liquidity) are both public.

## 30-second quickstart

```bash
pip install dex-chart-dashboard

dexscope add sol EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm --label WIF
dexscope serve            # open http://127.0.0.1:5066
```

Click a token to open its multi-timeframe candlestick page. No build step, no keys, no DB.
Use the chart checkboxes to enable EMA/RSI overlays, or open `/compare` to view normalized
watchlist performance side-by-side.

> Prefer to try it offline first? `python examples/quickstart.py` resamples a built-in 1h
> sample into 2h with zero network calls.

## Features

| | |
|---|---|
| 📈 Multi-timeframe | 1m · 5m · 15m · **30m** · 1h · **2h** · 4h · 1d candlesticks |
| 🧮 Local resampling | 30m from 15m, 2h from 1h — frames GeckoTerminal won't serve |
| 🐢 Free-tier safe | process-wide throttle + 429 backoff + 15-min on-disk cache |
| 🔑 Keyless | GeckoTerminal + DexScreener public endpoints only |
| 🎯 Your levels | per-token `entry` / `sl` / `tp1` / `tp2` drawn as lines |
| Technical overlays | optional EMA + RSI lines computed locally from the same public OHLCV candles |
| Compare view | `/compare` renders normalized percent-change mini-sparklines for the watchlist |
| PNG snapshots | `dexscope snapshot` exports candlestick PNGs when installed with `[viz]` |
| 🔌 Plain JSON watchlist | `{chain, address, label?, note?, entry?, sl?, tp1?, tp2?}` |
| 🖥️ Self-hosted | single Flask app, `127.0.0.1` by default |

## CLI

```bash
dexscope serve [--host --port --watchlist]   # run the dashboard
dexscope warm [TF ...]                        # pre-fetch + cache OHLC for the whole watchlist
dexscope resolve <chain> <address>            # print the best DexScreener pool for a token
dexscope add <chain> <address> [--label --entry --sl --tp1 --tp2 --note]
dexscope snapshot <chain> <address> [--timeframe 1h] [--out chart.png] [--ema 9] [--rsi 14]
```

Chains: `eth`, `bsc`, `base`, `sol` (aliases like `ethereum`, `bnb`, `solana` work too).

PNG export is optional:

```bash
pip install "dex-chart-dashboard[viz]"
dexscope snapshot sol EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm --ema 9 --rsi 14
```

Without the extra, the command exits with: `install dexscope[viz] to export PNG`.

## How it works

```
watchlist.json ──▶ DexScreener ──▶ live price / liquidity / best pool
                        │
   token page ──▶ GeckoTerminal OHLCV ──▶ [native: 1m/5m/15m/1h/4h/1d]
                        │                 [resampled: 30m←15m, 2h←1h]
                        ▼
              throttle + 429 backoff + 15-min disk cache
                        ▼
                 Chart.js candlesticks + your level lines
```

## FAQ

**Is this just an API wrapper?** No. The value is the parts that make the free APIs
*usable*: the 30m/2h resampling GeckoTerminal doesn't provide, and the throttle/backoff/cache
layer that stops a multi-timeframe page from rate-limiting itself.

**Do I need an API key?** No. Both data sources are keyless. There is nowhere to put a key.

**Does it touch my wallet / send my data anywhere?** No. It only does read-only GETs to
GeckoTerminal and DexScreener and serves a local web page. Your watchlist and caches stay
on disk (and are gitignored).

**Does it tell me what to buy?** No. It charts price and draws levels *you* set. Signal
scoring, paper-trading, and PnL simulation are deliberately out of scope.
EMA/RSI overlays and normalized compare charts are read-only views over public price data,
not financial advice.

## Related

- **Build the full runnable bot with Trawlkit**: https://github.com/baronguyen001
- 🧰 **[Trawlkit](https://github.com/baronguyen001)** — the full kit (scan → score → alert →
  paper-trade) this dashboard's charting engine was carved out of.
- 🔍 [wallet-cluster-detector](https://github.com/baronguyen001/wallet-cluster-detector) — Solana early-buyer cluster radar.
- 📊 [confluence-scanner](https://github.com/baronguyen001/confluence-scanner) — multi-factor TA confluence scanner.

## Development

```bash
git clone https://github.com/baronguyen001/dex-chart-dashboard
cd dex-chart-dashboard
pip install -e ".[dev]"
ruff check . && mypy src/dexscope && pytest --cov=dexscope
```

All tests run offline (fixtures + a fake HTTP client) — CI never calls the live providers.

## Star history

If this saved you a paid chart subscription, a ⭐ helps others find it.

[![Star History Chart](https://api.star-history.com/svg?repos=baronguyen001/dex-chart-dashboard&type=Date)](https://www.star-history.com/#baronguyen001/dex-chart-dashboard&Date)

## License

MIT © 2026 [baronguyen001](https://github.com/baronguyen001)

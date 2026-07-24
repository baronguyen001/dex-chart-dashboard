# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow SemVer.

## [0.4.0] - 2026-07-24

### Added
- MACD (`macd_values`) and Bollinger Bands (`bollinger_values`) as dependency-free overlays; both are opt-in arguments of `build_indicators` so existing payloads are unchanged.
- `dexscope export --indicators` appends `ema_*`, `rsi_*`, `macd*` and `bb_*` columns to the CSV/JSON export, with `--ema`/`--rsi` to pick periods.
- `dexscope alert --jsonl-out PATH` appends each check to a local append-only JSONL history (`alertlog`), so level hits can be reviewed offline later.

## [0.3.0] - 2026-07-13

### Added
- `dexscope alert` - one-shot read-only watchlist threshold check (entry/SL/TP distance), text/JSON, keyless.
- `dexscope export` - OHLCV candle export to CSV/JSON per token for offline analysis.
- `dexscope report` - terminal digest of the whole watchlist (price + latest EMA/RSI + distance-to-levels), text/JSON.

## [0.2.0] - 2026-06-15

### Added
- Added optional EMA and RSI overlays computed locally from fetched OHLCV candles.
- Added `/compare` for normalized percent-change watchlist mini-sparklines.
- Added `dexscope snapshot` PNG export behind the optional `[viz]` matplotlib extra.

## [0.1.0] - 2026-06-10

Initial release.

### Added
- `dexscope serve` - self-hosted Flask dashboard: watchlist table + per-token candlestick chart.
- Multi-timeframe charts (1m/5m/15m/30m/1h/2h/4h/1d) from **GeckoTerminal** OHLCV.
- **30m & 2h resampled locally** from 15m / 1h (GeckoTerminal serves neither natively).
- Process-wide request throttle + HTTP 429 backoff + 15-minute on-disk OHLC cache to stay under free-tier limits.
- **DexScreener** integration: best-liquidity pool resolution + batched live price/liquidity.
- Watchlist as plain JSON (`{chain, address, label?, note?, entry?, sl?, tp1?, tp2?}`); entry/SL/TP draw as level lines.
- CLI: `serve`, `warm`, `resolve`, `add`.
- No API keys required (both providers are keyless).

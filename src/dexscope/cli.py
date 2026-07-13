"""Command-line entry point: ``dexscope <command>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .alerts import build_alert_rows, render_alert_text
from .chains import GECKO_CHAINS, norm_chain
from .config import load_settings
from .dexscreener import DexScreenerClient
from .exporter import candles_to_csv, candles_to_json
from .gecko import GeckoClient
from .indicators import build_indicators
from .models import CHART_TIMEFRAMES, TIMEFRAME_SPECS
from .ratelimit import RateLimiter
from .report import build_report_rows, render_report_text
from .watchlist import add_entry, load_watchlist


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dexscope", description=__doc__)
    parser.add_argument("--version", action="version", version=f"dexscope {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="run the dashboard web app")
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.add_argument("--watchlist", default=None)
    p_serve.add_argument("--debug", action="store_true")

    p_warm = sub.add_parser("warm", help="pre-fetch + cache OHLC for every watchlist pool")
    p_warm.add_argument("timeframes", nargs="*", help=f"subset of {', '.join(CHART_TIMEFRAMES)}")

    p_resolve = sub.add_parser("resolve", help="print the best DexScreener pool for a token")
    p_resolve.add_argument("chain")
    p_resolve.add_argument("address")

    p_add = sub.add_parser("add", help="append a token to the watchlist")
    p_add.add_argument("chain")
    p_add.add_argument("address")
    p_add.add_argument("--label", default=None)
    p_add.add_argument("--note", default=None)
    p_add.add_argument("--entry", type=float, default=None)
    p_add.add_argument("--sl", type=float, default=None)
    p_add.add_argument("--tp1", type=float, default=None)
    p_add.add_argument("--tp2", type=float, default=None)

    p_snapshot = sub.add_parser("snapshot", help="export a token candlestick chart to PNG")
    p_snapshot.add_argument("chain")
    p_snapshot.add_argument("address")
    p_snapshot.add_argument("--timeframe", default="1h", choices=CHART_TIMEFRAMES)
    p_snapshot.add_argument("--out", default="chart.png")
    p_snapshot.add_argument("--ema", type=int, action="append", default=[], metavar="PERIOD")
    p_snapshot.add_argument("--rsi", type=int, default=None, metavar="PERIOD")

    p_alert = sub.add_parser("alert", help="one-shot watchlist threshold check")
    p_alert.add_argument("--watchlist", default=None)
    p_alert.add_argument("--format", choices=("text", "json"), default="text")
    p_alert.add_argument("--only-hit", action="store_true")

    p_export = sub.add_parser("export", help="export OHLCV candles to CSV or JSON")
    p_export.add_argument("chain")
    p_export.add_argument("address")
    p_export.add_argument("--timeframe", default="1h", choices=CHART_TIMEFRAMES)
    p_export.add_argument("--format", choices=("csv", "json"), default="csv")
    p_export.add_argument("--out", default=None)

    p_report = sub.add_parser("report", help="print a read-only watchlist digest")
    p_report.add_argument("--watchlist", default=None)
    p_report.add_argument("--timeframe", default="1h", choices=CHART_TIMEFRAMES)
    p_report.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    from .config import Settings
    from .web import create_app

    overrides: dict = {}
    if args.host:
        overrides["host"] = args.host
    if args.port:
        overrides["port"] = args.port
    if args.watchlist:
        from pathlib import Path

        overrides["watchlist_path"] = Path(args.watchlist).resolve()
    settings = load_settings()
    if overrides:
        settings = Settings(**{**settings.__dict__, **overrides})
    app = create_app(settings)
    print(
        f"dexscope serving http://{settings.host}:{settings.port}  "
        f"(watchlist: {settings.watchlist_path})"
    )
    app.run(host=settings.host, port=settings.port, debug=args.debug)
    return 0


def _cmd_warm(args: argparse.Namespace) -> int:
    settings = load_settings()
    gecko = GeckoClient(settings, RateLimiter(settings.rate_min_interval))
    dex = DexScreenerClient(settings)
    timeframes = [tf for tf in args.timeframes if tf in TIMEFRAME_SPECS] or list(CHART_TIMEFRAMES)

    rows = load_watchlist(settings.watchlist_path)
    print(f"Watchlist tokens: {len(rows)} | timeframes: {', '.join(timeframes)}")
    print("-" * 60)
    total = 0
    for i, row in enumerate(rows, 1):
        chain = row["chain"]
        if chain not in GECKO_CHAINS:
            continue
        pool = dex.resolve_pool(chain, row["address"]).get("pool")
        label = row.get("label") or row["address"][:10]
        if not pool:
            print(f"[{i}/{len(rows)}] {chain}:{label}  (no pool found)")
            continue
        print(f"[{i}/{len(rows)}] {chain}:{label}  pool {pool}")
        for tf in timeframes:
            candles = gecko.fetch(chain, pool, tf)
            total += len(candles)
            note = "" if candles else "  (no data / too fresh)"
            print(f"    {tf:>4}: {len(candles):>4} candles{note}")
    print("-" * 60)
    print(f"Done. {total} candles cached in {settings.cache_dir}")
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    settings = load_settings()
    dex = DexScreenerClient(settings)
    info = dex.resolve_pool(args.chain, args.address)
    if not info:
        print(f"No pool found for {norm_chain(args.chain)}:{args.address}", file=sys.stderr)
        return 1
    print(f"chain  : {norm_chain(args.chain)}")
    print(f"symbol : {info.get('symbol') or '-'}")
    print(f"pool   : {info.get('pool') or '-'}")
    print(f"price  : {info.get('price')}")
    print(f"liq    : {info.get('liq')}")
    print(f"url    : {info.get('url') or '-'}")
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    settings = load_settings()
    try:
        row = add_entry(
            settings.watchlist_path,
            args.chain,
            args.address,
            label=args.label,
            note=args.note,
            entry=args.entry,
            sl=args.sl,
            tp1=args.tp1,
            tp2=args.tp2,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Added {row['key']} to {settings.watchlist_path}")
    return 0


def _cmd_snapshot(args: argparse.Namespace) -> int:
    from .snapshot import VIZ_EXTRA_MESSAGE, export_snapshot

    settings = load_settings()
    dex = DexScreenerClient(settings)
    info = dex.resolve_pool(args.chain, args.address)
    if not info.get("pool"):
        print(f"No pool found for {norm_chain(args.chain)}:{args.address}", file=sys.stderr)
        return 1

    gecko = GeckoClient(settings, RateLimiter(settings.rate_min_interval))
    candles = gecko.fetch(args.chain, info["pool"], args.timeframe)
    if not candles:
        print("No candles available for snapshot", file=sys.stderr)
        return 1

    try:
        out = export_snapshot(
            candles,
            Path(args.out),
            title=info.get("symbol") or args.address[:10],
            timeframe=args.timeframe,
            ema_periods=tuple(args.ema),
            rsi_period=args.rsi,
        )
    except RuntimeError as exc:
        if str(exc) == VIZ_EXTRA_MESSAGE:
            print(str(exc), file=sys.stderr)
            return 1
        raise
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Wrote {out}")
    return 0


def _cmd_alert(args: argparse.Namespace) -> int:
    settings = load_settings()
    watchlist_path = Path(args.watchlist).resolve() if args.watchlist else settings.watchlist_path
    rows = load_watchlist(watchlist_path)
    dex = DexScreenerClient(settings)
    live = dex.live_prices([(row["chain"], row["address"]) for row in rows])
    alert_rows = build_alert_rows(rows, live, only_hit=args.only_hit)
    if args.format == "json":
        print(json.dumps(alert_rows, indent=2, ensure_ascii=False))
    else:
        print(render_alert_text(alert_rows))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    settings = load_settings()
    dex = DexScreenerClient(settings)
    info = dex.resolve_pool(args.chain, args.address)
    if not info.get("pool"):
        print(f"No pool found for {norm_chain(args.chain)}:{args.address}", file=sys.stderr)
        return 1

    gecko = GeckoClient(settings, RateLimiter(settings.rate_min_interval))
    candles = gecko.fetch(args.chain, info["pool"], args.timeframe)
    if not candles:
        print("No candles available for export", file=sys.stderr)
        return 1

    payload = candles_to_json(candles) if args.format == "json" else candles_to_csv(candles)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(payload, end="" if payload.endswith("\n") else "\n")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    settings = load_settings()
    watchlist_path = Path(args.watchlist).resolve() if args.watchlist else settings.watchlist_path
    rows = load_watchlist(watchlist_path)
    dex = DexScreenerClient(settings)
    gecko = GeckoClient(settings, RateLimiter(settings.rate_min_interval))
    live: dict[str, dict] = {}
    indicators_by_key: dict[str, dict] = {}

    for row in rows:
        info = dex.resolve_pool(row["chain"], row["address"])
        if info:
            live[row["key"]] = info
        pool = info.get("pool")
        if not pool:
            continue
        candles = gecko.fetch(row["chain"], pool, args.timeframe)
        indicators_by_key[row["key"]] = build_indicators(candles) if candles else {}

    report_rows = build_report_rows(rows, live, indicators_by_key)
    if args.format == "json":
        print(json.dumps(report_rows, indent=2, ensure_ascii=False))
    else:
        print(render_report_text(report_rows))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "serve": _cmd_serve,
        "warm": _cmd_warm,
        "resolve": _cmd_resolve,
        "add": _cmd_add,
        "snapshot": _cmd_snapshot,
        "alert": _cmd_alert,
        "export": _cmd_export,
        "report": _cmd_report,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())

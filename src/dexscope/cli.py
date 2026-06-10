"""Command-line entry point: ``dexscope <command>``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .chains import GECKO_CHAINS, norm_chain
from .config import load_settings
from .dexscreener import DexScreenerClient
from .gecko import GeckoClient
from .models import CHART_TIMEFRAMES, TIMEFRAME_SPECS
from .ratelimit import RateLimiter
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


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handlers = {
        "serve": _cmd_serve,
        "warm": _cmd_warm,
        "resolve": _cmd_resolve,
        "add": _cmd_add,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())

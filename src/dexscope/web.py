"""Flask app factory and routes.

Routes:
  GET  /                          watchlist table (live price/liq from DexScreener)
  GET  /token/<chain>/<address>   multi-timeframe candlestick chart for one token
  GET  /compare                   normalized watchlist mini-sparklines
  GET  /api/health                liveness + counts
  GET  /api/data                  the watchlist model as JSON
  POST /api/refresh-prices        refresh the live-price cache
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, abort, jsonify, render_template, request

from .chains import norm_chain
from .chart import build_chart_bundle
from .config import Settings, load_settings
from .dexscreener import DexScreenerClient
from .formatting import register_filters
from .gecko import GeckoClient
from .models import CHART_TIMEFRAMES
from .ratelimit import RateLimiter
from .util import read_json, to_float, write_json
from .watchlist import build_items, load_watchlist


def _live_cache(settings: Settings) -> dict[str, dict]:
    cached = read_json(settings.live_cache_path, {})
    prices = cached.get("prices") if isinstance(cached, dict) else None
    return prices if isinstance(prices, dict) else {}


def _period_list(raw: str | None, fallback: tuple[int, ...]) -> tuple[int, ...]:
    if raw is None:
        return fallback
    out: list[int] = []
    for chunk in raw.replace(";", ",").split(","):
        try:
            period = int(chunk.strip())
        except ValueError:
            continue
        if 1 <= period <= 300 and period not in out:
            out.append(period)
    return tuple(out) or fallback


def _period(raw: str | None, fallback: int) -> int:
    try:
        value = int(raw or "")
    except ValueError:
        return fallback
    return value if 1 <= value <= 300 else fallback


def _compare_points(candles: list[dict]) -> list[float | None]:
    closes = [to_float(row.get("close")) for row in candles]
    base = next((value for value in closes if value not in (None, 0.0)), None)
    if base is None:
        return []
    return [None if value is None else ((value - base) / base) * 100.0 for value in closes]


def _compare_labels(candles: list[dict]) -> list[str]:
    return [str(i + 1) for i, _ in enumerate(candles)]


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_settings()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["JSON_SORT_KEYS"] = False
    app.config["DEXSCOPE_SETTINGS"] = settings
    register_filters(app)

    limiter = RateLimiter(settings.rate_min_interval)
    gecko = GeckoClient(settings, limiter)
    dex = DexScreenerClient(settings)

    def build_model() -> dict:
        watchlist = load_watchlist(settings.watchlist_path)
        items = build_items(watchlist, _live_cache(settings))
        return {"items": items, "watchlist_path": str(settings.watchlist_path)}

    @app.route("/")
    def index():
        return render_template("index.html", **build_model())

    @app.route("/token/<chain>/<path:address>")
    def token_detail(chain: str, address: str):
        chain = norm_chain(chain)
        watchlist = load_watchlist(settings.watchlist_path)
        row = next((r for r in watchlist if r["chain"] == chain and r["address"] == address), None)
        # Allow charting any token, even if it isn't saved on the watchlist yet.
        item = dict(row) if row else {"chain": chain, "address": address, "label": "", "note": ""}
        pool_info = dex.resolve_pool(chain, address)
        item["pool"] = pool_info.get("pool") or ""
        item["url"] = pool_info.get("url") or item.get("url") or ""
        item["symbol"] = item.get("label") or pool_info.get("symbol") or "-"
        item["price"] = pool_info.get("price")
        if not item["pool"]:
            abort(404)
        chart = build_chart_bundle(
            gecko,
            item,
            ema_periods=_period_list(request.args.get("ema"), (9, 21)),
            rsi_period=_period(request.args.get("rsi"), 14),
        )
        return render_template("token.html", item=item, chart=chart)

    @app.route("/compare")
    def compare():
        timeframe = request.args.get("timeframe") or "1h"
        if timeframe not in CHART_TIMEFRAMES:
            timeframe = "1h"

        watchlist = load_watchlist(settings.watchlist_path)
        rows = []
        for row in watchlist:
            pool_info = dex.resolve_pool(row["chain"], row["address"])
            pool = pool_info.get("pool") or ""
            candles = gecko.fetch(row["chain"], pool, timeframe) if pool else []
            rows.append(
                {
                    "label": row.get("label") or pool_info.get("symbol") or row["address"][:10],
                    "chain": row["chain"],
                    "address": row["address"],
                    "url": pool_info.get("url") or "",
                    "labels": _compare_labels(candles),
                    "points": _compare_points(candles),
                    "count": len(candles),
                }
            )

        return render_template(
            "compare.html",
            rows=rows,
            timeframe=timeframe,
            timeframes=CHART_TIMEFRAMES,
        )

    @app.get("/api/health")
    def api_health():
        model = build_model()
        return jsonify(
            {
                "ok": True,
                "items": len(model["items"]),
                "watchlist_path": model["watchlist_path"],
                "watchlist_exists": settings.watchlist_path.exists(),
            }
        )

    @app.get("/api/data")
    def api_data():
        return jsonify(build_model())

    @app.post("/api/refresh-prices")
    def api_refresh_prices():
        watchlist = load_watchlist(settings.watchlist_path)
        prices = dex.live_prices([(r["chain"], r["address"]) for r in watchlist])
        write_json(
            settings.live_cache_path,
            {
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "prices": prices,
            },
        )
        return jsonify({"ok": True, "updated": len(prices)})

    return app

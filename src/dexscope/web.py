"""Flask app factory and routes.

Routes:
  GET  /                          watchlist table (live price/liq from DexScreener)
  GET  /token/<chain>/<address>   multi-timeframe candlestick chart for one token
  GET  /api/health                liveness + counts
  GET  /api/data                  the watchlist model as JSON
  POST /api/refresh-prices        refresh the live-price cache
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Flask, abort, jsonify, render_template

from .chains import norm_chain
from .chart import build_chart_bundle
from .config import Settings, load_settings
from .dexscreener import DexScreenerClient
from .formatting import register_filters
from .gecko import GeckoClient
from .ratelimit import RateLimiter
from .util import read_json, write_json
from .watchlist import build_items, load_watchlist


def _live_cache(settings: Settings) -> dict[str, dict]:
    cached = read_json(settings.live_cache_path, {})
    prices = cached.get("prices") if isinstance(cached, dict) else None
    return prices if isinstance(prices, dict) else {}


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
        chart = build_chart_bundle(gecko, item)
        return render_template("token.html", item=item, chart=chart)

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

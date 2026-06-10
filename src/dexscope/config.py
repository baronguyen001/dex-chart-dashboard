"""Runtime settings, loaded from ``DEXSCOPE_*`` environment variables with sane defaults.

No API keys are ever read here — both data providers are keyless public endpoints.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from . import __version__

DEXSCREENER_BASE = "https://api.dexscreener.com"
GECKO_BASE = "https://api.geckoterminal.com/api/v2"


def _default_root() -> Path:
    """Project root for relative defaults: cwd, so a user's data/ stays in their project."""
    return Path(os.getenv("DEXSCOPE_ROOT", ".")).resolve()


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 5066
    cache_dir: Path = Path("data/ohlc_cache")
    watchlist_path: Path = Path("watchlist.json")
    live_cache_path: Path = Path("data/live_prices_cache.json")
    cache_ttl_sec: int = 15 * 60
    # ~27 requests/min, comfortably under GeckoTerminal's free ~30 RPM cap.
    rate_min_interval: float = 2.2
    user_agent: str = f"dexscope/{__version__}"


def _env(env: Mapping[str, str] | None, key: str) -> str | None:
    source = env if env is not None else os.environ
    value = source.get(key)
    return value if value not in (None, "") else None


def _resolve(root: Path, value: str | None, fallback: Path) -> Path:
    path = Path(value) if value else fallback
    return path if path.is_absolute() else (root / path)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from ``DEXSCOPE_*`` env vars (or an explicit mapping)."""
    source = env if env is not None else os.environ
    root = Path(source.get("DEXSCOPE_ROOT", ".")).resolve()
    defaults = Settings()

    def num(key: str, fallback: float) -> float:
        raw = _env(env, key)
        if raw is None:
            return fallback
        try:
            return float(raw)
        except ValueError:
            return fallback

    return Settings(
        host=_env(env, "DEXSCOPE_HOST") or defaults.host,
        port=int(num("DEXSCOPE_PORT", defaults.port)),
        cache_dir=_resolve(root, _env(env, "DEXSCOPE_CACHE_DIR"), defaults.cache_dir),
        watchlist_path=_resolve(root, _env(env, "DEXSCOPE_WATCHLIST"), defaults.watchlist_path),
        live_cache_path=_resolve(root, _env(env, "DEXSCOPE_LIVE_CACHE"), defaults.live_cache_path),
        cache_ttl_sec=int(num("DEXSCOPE_CACHE_TTL_SEC", defaults.cache_ttl_sec)),
        rate_min_interval=num("DEXSCOPE_RATE_MIN_INTERVAL", defaults.rate_min_interval),
        user_agent=_env(env, "DEXSCOPE_USER_AGENT") or defaults.user_agent,
    )

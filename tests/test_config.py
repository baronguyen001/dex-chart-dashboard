from __future__ import annotations

from pathlib import Path

from dexscope.config import Settings, _default_root, load_settings


def test_default_root_resolves(tmp_path):
    root = _default_root()
    assert root.is_absolute()


def test_load_settings_uses_defaults_when_env_empty():
    settings = load_settings({})
    assert settings == Settings(
        host=settings.host,
        port=settings.port,
        cache_dir=settings.cache_dir,
        watchlist_path=settings.watchlist_path,
        live_cache_path=settings.live_cache_path,
        cache_ttl_sec=settings.cache_ttl_sec,
        rate_min_interval=settings.rate_min_interval,
        user_agent=settings.user_agent,
    )
    assert settings.host == "127.0.0.1"
    assert settings.port == 5066
    assert settings.cache_ttl_sec == 15 * 60


def test_load_settings_applies_env_overrides(tmp_path):
    root = tmp_path.resolve()
    settings = load_settings(
        {
            "DEXSCOPE_ROOT": str(root),
            "DEXSCOPE_HOST": "0.0.0.0",
            "DEXSCOPE_PORT": "8080",
            "DEXSCOPE_CACHE_TTL_SEC": "60",
            "DEXSCOPE_RATE_MIN_INTERVAL": "1.5",
            "DEXSCOPE_USER_AGENT": "custom-agent",
            "DEXSCOPE_CACHE_DIR": "cache",
        }
    )
    assert settings.host == "0.0.0.0"
    assert settings.port == 8080
    assert settings.cache_ttl_sec == 60
    assert settings.rate_min_interval == 1.5
    assert settings.user_agent == "custom-agent"
    # relative path is resolved against DEXSCOPE_ROOT
    assert settings.cache_dir == root / "cache"


def test_load_settings_numeric_fallback_and_absolute_path():
    abs_dir = Path("/tmp/abs_cache").resolve()
    settings = load_settings(
        {
            "DEXSCOPE_PORT": "not-an-int",
            "DEXSCOPE_RATE_MIN_INTERVAL": "nope",
            "DEXSCOPE_CACHE_DIR": str(abs_dir),
        }
    )
    # invalid numbers fall back to defaults
    assert settings.port == 5066
    assert settings.rate_min_interval == Settings().rate_min_interval
    # an absolute override path is kept as-is
    assert settings.cache_dir == abs_dir

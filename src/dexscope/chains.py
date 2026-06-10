"""Chain name normalization and the DexScreener / GeckoTerminal slug maps.

GeckoTerminal and DexScreener use different network slugs for the same chain, so the
dashboard normalizes every user-supplied chain to a short canonical key first, then
looks up the right slug per provider.
"""

from __future__ import annotations

# canonical short key -> itself; many aliases collapse onto these four.
CHAIN_ALIASES: dict[str, str] = {
    "ethereum": "eth",
    "eth": "eth",
    "bnb": "bsc",
    "binance": "bsc",
    "bsc": "bsc",
    "base": "base",
    "coinbase": "base",
    "solana": "sol",
    "sol": "sol",
}

# canonical key -> DexScreener network slug
DEX_CHAINS: dict[str, str] = {
    "eth": "ethereum",
    "bsc": "bsc",
    "base": "base",
    "sol": "solana",
}

# canonical key -> GeckoTerminal network slug
GECKO_CHAINS: dict[str, str] = {
    "eth": "eth",
    "bsc": "bsc",
    "base": "base",
    "sol": "solana",
}


def norm_chain(value: str | None) -> str:
    """Lowercase + map any known alias to its canonical short key."""
    raw = (value or "").strip().lower()
    return CHAIN_ALIASES.get(raw, raw)


def token_key(chain: str | None, address: str | None) -> str:
    """Stable dict key for a (chain, address) pair. Address case is preserved because
    Solana base58 addresses are case-sensitive."""
    return f"{norm_chain(chain)}:{address or ''}"

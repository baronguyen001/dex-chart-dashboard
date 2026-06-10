"""DexScreener client: resolve a token's best pool and fetch live price/liquidity.

DexScreener is keyless and gives us two things GeckoTerminal's OHLCV endpoint does not:
the highest-liquidity *pool address* for a token (needed before we can fetch candles)
and a fast batched live price/liquidity lookup for the watchlist table.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

import httpx

from .chains import DEX_CHAINS, norm_chain, token_key
from .config import DEXSCREENER_BASE, Settings
from .util import to_float

ClientFactory = Callable[..., httpx.Client]


class DexScreenerClient:
    def __init__(self, settings: Settings, *, client_factory: ClientFactory = httpx.Client) -> None:
        self.settings = settings
        self._client_factory = client_factory

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.settings.user_agent}

    def resolve_pool(self, chain: str, address: str) -> dict:
        """Highest-liquidity DexScreener pool for a token address.

        Returns ``{pool, url, price, symbol, liq}`` or ``{}`` when nothing is found.
        """
        chain = norm_chain(chain)
        dex_chain = DEX_CHAINS.get(chain)
        if not dex_chain or not address:
            return {}
        try:
            with self._client_factory(headers=self._headers(), timeout=20) as client:
                response = client.get(f"{DEXSCREENER_BASE}/tokens/v1/{dex_chain}/{address}")
                if response.status_code != 200:
                    return {}
                best: dict | None = None
                for pair in response.json() or []:
                    liq = to_float((pair.get("liquidity") or {}).get("usd")) or 0.0
                    if best is None or liq > best["liq"]:
                        base = pair.get("baseToken") or {}
                        best = {
                            "liq": liq,
                            "pool": pair.get("pairAddress") or "",
                            "url": pair.get("url") or "",
                            "price": to_float(pair.get("priceUsd")),
                            "symbol": base.get("symbol") or "",
                        }
                return best or {}
        except (httpx.HTTPError, ValueError):
            return {}

    def live_prices(self, tokens: list[tuple[str, str]]) -> dict[str, dict]:
        """Batched live price/liquidity for ``(chain, address)`` pairs.

        Keyed by :func:`token_key`. DexScreener accepts up to 30 addresses per call.
        """
        by_chain: dict[str, list[str]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for chain, address in tokens:
            chain = norm_chain(chain)
            if not address or chain not in DEX_CHAINS:
                continue
            key = (chain, address)
            if key in seen:
                continue
            seen.add(key)
            by_chain[chain].append(address)

        out: dict[str, dict] = {}
        try:
            with self._client_factory(headers=self._headers(), timeout=20) as client:
                for chain, addresses in by_chain.items():
                    dex_chain = DEX_CHAINS[chain]
                    for i in range(0, len(addresses), 30):
                        batch = addresses[i : i + 30]
                        try:
                            response = client.get(
                                f"{DEXSCREENER_BASE}/tokens/v1/{dex_chain}/{','.join(batch)}"
                            )
                        except httpx.HTTPError:
                            continue
                        if response.status_code != 200:
                            continue
                        best_by_addr: dict[str, dict] = {}
                        for pair in response.json() or []:
                            base = pair.get("baseToken") or {}
                            addr = base.get("address")
                            if not addr:
                                continue
                            liq = to_float((pair.get("liquidity") or {}).get("usd")) or 0.0
                            current = best_by_addr.get(addr)
                            if current is None or liq > current["liq"]:
                                best_by_addr[addr] = {
                                    "price": to_float(pair.get("priceUsd")),
                                    "liq": liq,
                                    "url": pair.get("url") or "",
                                    "symbol": base.get("symbol") or "",
                                }
                        for addr, row in best_by_addr.items():
                            if row.get("price") is not None:
                                out[token_key(chain, addr)] = row
        except (httpx.HTTPError, ValueError):
            return out
        return out

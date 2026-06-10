from __future__ import annotations

from conftest import FakeResponse, client_factory_for, load_fixture
from dexscope.config import Settings
from dexscope.dexscreener import DexScreenerClient


def test_resolve_pool_picks_highest_liquidity():
    fixture = load_fixture("dexscreener_token.json")
    dex = DexScreenerClient(
        Settings(), client_factory=client_factory_for(lambda u, p: FakeResponse(200, fixture))
    )
    info = dex.resolve_pool("sol", "EXAMPLEtokenAddress1111111111111111111111111")
    assert (
        info["pool"] == "ExamplePool1111111111111111111111111111111"
    )  # the 250k-liq pool, not 90k
    assert info["price"] == 1.30
    assert info["symbol"] == "EXMPL"


def test_resolve_pool_unknown_chain():
    dex = DexScreenerClient(Settings())
    assert dex.resolve_pool("polygon", "0xabc") == {}


def test_live_prices_keyed_by_token_key():
    fixture = load_fixture("dexscreener_token.json")
    dex = DexScreenerClient(
        Settings(), client_factory=client_factory_for(lambda u, p: FakeResponse(200, fixture))
    )
    out = dex.live_prices([("sol", "EXAMPLEtokenAddress1111111111111111111111111")])
    key = "sol:EXAMPLEtokenAddress1111111111111111111111111"
    assert key in out
    assert out[key]["price"] == 1.30
    assert out[key]["liq"] == 250000.0  # best pool's liquidity

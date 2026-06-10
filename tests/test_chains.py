from __future__ import annotations

from dexscope.chains import DEX_CHAINS, GECKO_CHAINS, norm_chain, token_key


def test_norm_chain_aliases():
    assert norm_chain("Ethereum") == "eth"
    assert norm_chain("ETH") == "eth"
    assert norm_chain("BNB") == "bsc"
    assert norm_chain("binance") == "bsc"
    assert norm_chain("Solana") == "sol"
    assert norm_chain("coinbase") == "base"


def test_norm_chain_unknown_passthrough():
    assert norm_chain("polygon") == "polygon"
    assert norm_chain(None) == ""


def test_token_key_preserves_address_case():
    # Solana base58 addresses are case-sensitive, so the address half must NOT be lowercased.
    key = token_key("SOL", "AbCdEf123")
    assert key == "sol:AbCdEf123"


def test_provider_slugs_cover_canonical_keys():
    for key in ("eth", "bsc", "base", "sol"):
        assert key in DEX_CHAINS
        assert key in GECKO_CHAINS

from __future__ import annotations

from dexscope.formatting import addr, money, pct, price, xnum


def test_money():
    assert money(1500) == "$1.50K"
    assert money(2_000_000) == "$2.00M"
    assert money(3_500_000_000) == "$3.50B"
    assert money(-500) == "-$500.00"
    assert money(None) == "-"


def test_price_tiers():
    assert price(0) == "0"
    assert price(1234.5) == "1,234.50"
    assert price(12.3456) == "12.3456"
    assert price(None) == "-"


def test_pct_and_xnum():
    assert pct(5) == "+5.0%"
    assert pct(-2.5) == "-2.5%"
    assert pct(None) == "-"
    assert xnum(2) == "2.00x"
    assert xnum(None) == "-"


def test_addr_truncation():
    assert addr("0x1234567890abcdef1234") == "0x1234...1234"
    assert addr("short") == "short"
    assert addr(None) == "-"

from __future__ import annotations

import re

from dexscope.formatting import dt, price


def test_price_small_tiers():
    assert price(0.05) == "0.050000"
    assert price(0.0005) == "0.0005"
    assert price(0.00000005) == "0.00000005"


def test_dt_valid_invalid_and_none():
    rendered = dt("2026-01-02T03:04:05Z")
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", rendered)
    assert dt("not-a-date") == "-"
    assert dt(None) == "-"

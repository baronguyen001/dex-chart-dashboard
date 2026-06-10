"""Display formatters, also registered as Jinja filters on the Flask app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .util import parse_iso, to_float

if TYPE_CHECKING:
    from flask import Flask


def money(value: Any) -> str:
    n = to_float(value)
    if n is None:
        return "-"
    sign = "-" if n < 0 else ""
    n_abs = abs(n)
    if n_abs >= 1_000_000_000:
        return f"{sign}${n_abs / 1_000_000_000:.2f}B"
    if n_abs >= 1_000_000:
        return f"{sign}${n_abs / 1_000_000:.2f}M"
    if n_abs >= 1_000:
        return f"{sign}${n_abs / 1_000:.2f}K"
    return f"{sign}${n_abs:,.2f}"


def price(value: Any) -> str:
    n = to_float(value)
    if n is None:
        return "-"
    if n == 0:
        return "0"
    n_abs = abs(n)
    if n_abs >= 1000:
        return f"{n:,.2f}"
    if n_abs >= 1:
        return f"{n:,.4f}"
    if n_abs >= 0.01:
        return f"{n:.6f}"
    if n_abs >= 0.0001:
        return f"{n:.8f}".rstrip("0").rstrip(".")
    return f"{n:.12f}".rstrip("0").rstrip(".")


def pct(value: Any) -> str:
    n = to_float(value)
    if n is None:
        return "-"
    return f"{n:+.1f}%"


def xnum(value: Any) -> str:
    n = to_float(value)
    if n is None:
        return "-"
    return f"{n:.2f}x"


def dt(value: Any) -> str:
    parsed = parse_iso(value)
    if not parsed:
        return "-"
    return parsed.astimezone().strftime("%Y-%m-%d %H:%M")


def addr(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 14:
        return text or "-"
    return f"{text[:6]}...{text[-4:]}"


def register_filters(app: Flask) -> None:
    for name, func in (
        ("money", money),
        ("price", price),
        ("pct", pct),
        ("xnum", xnum),
        ("dt", dt),
        ("addr", addr),
    ):
        app.add_template_filter(func, name)

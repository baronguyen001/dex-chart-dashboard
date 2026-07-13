from __future__ import annotations

from dexscope.alerts import build_alert_rows, evaluate_levels, render_alert_text


def _row() -> dict:
    return {
        "key": "sol:A",
        "chain": "sol",
        "address": "A",
        "label": "ALPHA",
        "entry": 1.0,
        "sl": 0.8,
        "tp1": 1.5,
        "tp2": 2.0,
    }


def test_evaluate_levels_marks_crossed_stop_loss():
    verdict = evaluate_levels(_row(), 0.75)
    assert verdict["status"] == "BELOW_SL"
    assert verdict["hit"] is True
    assert [level["name"] for level in verdict["levels"] if level["hit"]] == ["entry", "sl"]


def test_evaluate_levels_marks_near_uncrossed_level():
    verdict = evaluate_levels(_row(), 1.48)
    assert verdict["status"] == "NEAR_TP1"
    assert verdict["hit"] is False
    assert verdict["nearest_level"] == "tp1"
    assert round(verdict["nearest_distance_pct"], 2) == -1.33


def test_evaluate_levels_handles_missing_price_and_levels():
    assert evaluate_levels(_row(), None)["status"] == "NO_PRICE"
    assert evaluate_levels({"key": "sol:A", "chain": "sol", "address": "A"}, 1.0)["status"] == (
        "NO_LEVELS"
    )


def test_build_alert_rows_can_filter_to_hits_only():
    rows = [_row(), {**_row(), "key": "sol:B", "address": "B", "tp1": 1.1}]
    live = {
        "sol:A": {"price": 1.2, "symbol": "AAA"},
        "sol:B": {"price": 1.2, "symbol": "BBB"},
    }
    out = build_alert_rows(rows, live, only_hit=True)
    assert [row["symbol"] for row in out] == ["BBB"]
    assert out[0]["status"] == "ABOVE_TP1"


def test_render_alert_text_formats_table_and_empty_state():
    row = build_alert_rows([_row()], {"sol:A": {"price": 1.48, "symbol": "AAA"}})[0]
    text = render_alert_text([row])
    assert "TOKEN" in text
    assert "AAA" in text
    assert "NEAR_TP1" in text
    assert render_alert_text([]) == "No watchlist levels matched."

from __future__ import annotations

import json
from pathlib import Path

from dexscope.alertlog import (
    RECORD_FIELDS,
    alert_row_to_record,
    alert_rows_to_jsonl,
    append_jsonl,
    read_jsonl,
)

ROW = {
    "key": "solana:So11111111111111111111111111111111111111112",
    "chain": "solana",
    "address": "So11111111111111111111111111111111111111112",
    "label": "SOL",
    "symbol": "SOL",
    "url": "https://dexscreener.com/solana/abc",
    "price": 148.2,
    "status": "NEAR_TP1",
    "hit": False,
    "nearest_level": "tp1",
    "nearest_distance_pct": -1.83,
    "levels": [
        {"name": "entry", "value": 120.0, "distance_pct": 23.5, "hit": True},
        {"name": "tp1", "value": 150.0, "distance_pct": -1.2, "hit": False},
        {"name": "sl", "value": 100.0, "distance_pct": 48.2, "hit": True},
    ],
}

ROW_WITHOUT_LEVELS = {
    "key": "eth:0xabc",
    "chain": "ethereum",
    "address": "0xabc",
    "symbol": "ABC",
    "price": 1.0,
    "status": "NO_LEVELS",
    "hit": False,
    "nearest_level": None,
    "nearest_distance_pct": None,
}


def test_record_has_a_stable_minimal_shape():
    record = alert_row_to_record(ROW, checked_at=1234567890)
    assert list(record) == list(RECORD_FIELDS)
    assert record["checked_at"] == 1234567890
    assert record["key"] == ROW["key"]
    assert record["price"] == 148.2
    assert record["nearest_distance_pct"] == -1.83
    assert "url" not in record
    assert "label" not in record
    assert "levels" not in record


def test_record_collects_hit_levels_sorted():
    assert alert_row_to_record(ROW, checked_at=1)["levels_hit"] == ["entry", "sl"]


def test_record_levels_hit_is_empty_without_hits():
    assert alert_row_to_record(ROW_WITHOUT_LEVELS, checked_at=1)["levels_hit"] == []
    row = {**ROW, "levels": [{"name": "entry", "hit": False}, {"name": "tp1"}]}
    assert alert_row_to_record(row, checked_at=1)["levels_hit"] == []


def test_record_coerces_numeric_strings_and_missing_values():
    row = {**ROW, "price": "148.2", "nearest_distance_pct": None}
    record = alert_row_to_record(row, checked_at=1)
    assert record["price"] == 148.2
    assert record["nearest_distance_pct"] is None
    assert record["hit"] is False


def test_jsonl_of_no_rows_is_empty():
    assert alert_rows_to_jsonl([], checked_at=1) == ""


def test_jsonl_writes_one_compact_object_per_line():
    payload = alert_rows_to_jsonl([ROW, ROW_WITHOUT_LEVELS], checked_at=42)
    lines = payload.splitlines()
    assert len(lines) == 2
    assert payload.endswith("\n")
    assert "\n  " not in payload
    assert json.loads(lines[0])["checked_at"] == 42
    assert json.loads(lines[1])["key"] == ROW_WITHOUT_LEVELS["key"]


def test_append_creates_the_file_and_counts_lines(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    payload = alert_rows_to_jsonl([ROW], checked_at=1)
    assert append_jsonl(log, payload) == 1
    assert log.read_text(encoding="utf-8") == payload


def test_append_creates_missing_parent_directories(tmp_path: Path):
    log = tmp_path / "nested" / "deeper" / "alerts.jsonl"
    assert append_jsonl(log, '{"a": 1}\n') == 1
    assert log.exists()


def test_append_of_empty_payload_touches_nothing(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    assert append_jsonl(log, "") == 0
    assert not log.exists()

    log.write_bytes(b'{"a": 1}\n')
    assert append_jsonl(log, "") == 0
    assert log.read_bytes() == b'{"a": 1}\n'


def test_append_grows_the_log_and_keeps_earlier_lines(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    first = alert_rows_to_jsonl([ROW], checked_at=1)
    second = alert_rows_to_jsonl([ROW, ROW_WITHOUT_LEVELS], checked_at=2)
    assert append_jsonl(log, first) == 1
    assert append_jsonl(log, second) == 2

    records = read_jsonl(log)
    assert len(records) == 3
    assert [record["checked_at"] for record in records] == [1, 2, 2]


def test_append_keeps_unix_newlines_on_every_platform(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    append_jsonl(log, '{"a": 1}\n')
    raw = log.read_bytes()
    assert b"\r\n" not in raw
    assert raw.endswith(b"\n")


def test_read_of_a_missing_log_is_empty(tmp_path: Path):
    assert read_jsonl(tmp_path / "never-written.jsonl") == []


def test_read_skips_blank_lines(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    log.write_text('\n\n{"a": 1}\n  \n', encoding="utf-8")
    assert read_jsonl(log) == [{"a": 1}]
    log.write_text("\n  \n", encoding="utf-8")
    assert read_jsonl(log) == []


def test_roundtrip_preserves_every_record_field(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    append_jsonl(log, alert_rows_to_jsonl([ROW], checked_at=123))
    recovered = read_jsonl(log)[0]
    assert recovered == alert_row_to_record(ROW, checked_at=123)

from __future__ import annotations

from datetime import datetime, timezone

from dexscope.util import iso, parse_iso, read_json, to_float, utcnow, write_json


def test_to_float_rejects_unparseable_and_nonfinite():
    assert to_float(None) is None
    assert to_float("") is None
    assert to_float("abc") is None
    assert to_float(object()) is None
    assert to_float(float("nan")) is None
    assert to_float(float("inf")) is None
    assert to_float("1.5") == 1.5
    assert to_float(3) == 3.0


def test_iso_roundtrip_and_none():
    assert iso(None) is None
    assert iso(datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)) == "2026-01-02T03:04:05Z"


def test_parse_iso_handles_z_naive_and_garbage():
    assert parse_iso("") is None
    assert parse_iso("not-a-date") is None
    parsed_z = parse_iso("2026-01-02T03:04:05Z")
    assert parsed_z is not None and parsed_z.tzinfo is not None
    naive = parse_iso("2026-01-02T03:04:05")
    assert naive is not None and naive.tzinfo == timezone.utc


def test_utcnow_is_tz_aware():
    assert utcnow().tzinfo is not None


def test_read_json_default_missing_and_malformed(tmp_path):
    missing = tmp_path / "nope.json"
    assert read_json(missing, {"d": 1}) == {"d": 1}

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert read_json(bad, []) == []


def test_write_then_read_json_roundtrip(tmp_path):
    target = tmp_path / "nested" / "data.json"
    payload = {"a": 1, "b": ["x", "y"]}
    write_json(target, payload)
    assert target.exists()
    assert read_json(target, None) == payload

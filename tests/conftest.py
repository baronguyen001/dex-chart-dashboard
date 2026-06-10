"""Shared test helpers. All tests run fully offline — no real provider calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


class FakeClient:
    """Context-manager stand-in for httpx.Client driven by a handler(url, params)."""

    def __init__(self, handler: Callable[[str, dict], FakeResponse], **_: Any):
        self._handler = handler

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def get(self, url: str, params: dict | None = None) -> FakeResponse:
        return self._handler(url, params or {})


def client_factory_for(handler: Callable[[str, dict], FakeResponse]) -> Callable[..., FakeClient]:
    def factory(**kwargs: Any) -> FakeClient:
        return FakeClient(handler)

    return factory

"""Fake adapter for deterministic testing — supports structured status."""

from __future__ import annotations

import json
import time
from typing import Any

from .base import LLMAdapter, LLMResponse, STATUS_OK


DEFAULT_FAKE_RESPONSE: dict[str, Any] = {
    "schema_version": "0.2",
    "real_goal": "Test fake response",
    "friction_hypotheses": [
        {"type": "verification", "confidence": 0.7, "evidence": ["user asked for review"], "uncertainty": "low"}
    ],
    "task_hypotheses": [
        {
            "title": "Review the item",
            "expected_deliverable": "written evaluation",
            "suggested_routes": ["MARKET", "AI"],
            "requires_user_action": False,
            "sensitivity": "low",
        }
    ],
    "profession_terms": ["fake reviewer"],
    "service_terms": ["fake review service"],
    "query_terms": ["fake query"],
    "unknown_dialect_hypotheses": [],
    "warnings": [],
}


class FakeAdapter:
    def __init__(self, response: dict[str, Any] | None = None,
                 latency_ms: float = 0.0,
                 error: type[BaseException] | None = None,
                 status: str = STATUS_OK,
                 error_type: str = ""):
        self._response = response or DEFAULT_FAKE_RESPONSE
        self._latency_ms = latency_ms
        self._error = error
        self._status = status
        self._error_type = error_type

    def complete_json(
        self, *, system: str, user_payload: dict[str, object],
        schema: dict[str, object], timeout_seconds: float, max_tokens: int = 1024,
    ) -> LLMResponse:
        if self._latency_ms:
            time.sleep(self._latency_ms / 1000.0)
        if self._error is not None:
            raise self._error("fake adapter error")
        payload = self._response() if callable(self._response) else dict(self._response)
        return LLMResponse(
            provider="fake", model="fake-model",
            raw_text=json.dumps(payload, ensure_ascii=False),
            parsed=payload, latency_ms=self._latency_ms,
            status=self._status if not self._error else STATUS_OK,
        )

    def __instancecheck__(self, instance: object) -> bool:
        return isinstance(instance, LLMAdapter)


class FakeAdapterWithStatus(FakeAdapter):
    """Fake that returns a specific LLMResponse status without raising."""
    def complete_json(self, **kw):
        return LLMResponse(provider="fake", model="x", status=self._status,
                           error_type=self._error_type, warnings=[])

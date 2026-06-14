"""Provider-independent LLM adapter protocol and response model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable

# ── Status strings ────────────────────────────────────────────────────

STATUS_NOT_CONFIGURED = "not_configured"
STATUS_OK = "ok"
STATUS_TIMEOUT = "timeout"
STATUS_CONNECTION_ERROR = "connection_error"
STATUS_AUTH_ERROR = "auth_error"
STATUS_HTTP_ERROR = "http_error"
STATUS_INVALID_JSON = "invalid_json"
STATUS_SCHEMA_ERROR = "schema_error"
STATUS_RESPONSE_TOO_LARGE = "response_too_large"
STATUS_PROMPT_INJECTION = "prompt_injection_warning"


@dataclass
class LLMResponse:
    provider: str
    model: str
    raw_text: str = ""
    parsed: dict[str, Any] | None = None
    latency_ms: float = 0.0
    usage: dict[str, int] | None = None
    request_id: str = ""
    warnings: list[str] = field(default_factory=list)
    # ── v0.2 review: structured status ──
    status: str = STATUS_OK
    error_type: str = ""
    http_status: int | None = None

    @property
    def success(self) -> bool:
        return self.parsed is not None


@runtime_checkable
class LLMAdapter(Protocol):
    def complete_json(
        self,
        *,
        system: str,
        user_payload: dict[str, object],
        schema: dict[str, object],
        timeout_seconds: float,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...


LLMFactory = Callable[[], LLMAdapter]

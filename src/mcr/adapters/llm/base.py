"""Provider-independent LLM adapter protocol and response model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from collections.abc import Callable


@dataclass
class LLMResponse:
    """A structured response from any compatible LLM endpoint.

    Keys:
    - provider: transport label (e.g. "openai_compatible", "fake").
    - model: resolved model name.
    - parsed: deserialized JSON dict; None when parsing failed.
    - latency_ms: round-trip wall-clock milliseconds.
    - usage: optional token counts.
    - request_id: optional provider-issued identifier.
    - warnings: human-readable notes (redaction applied, injection detected, etc.).
    """

    provider: str
    model: str
    raw_text: str = ""
    parsed: dict[str, Any] | None = None
    latency_ms: float = 0.0
    usage: dict[str, int] | None = None
    request_id: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.parsed is not None


@runtime_checkable
class LLMAdapter(Protocol):
    """Provider-independent protocol for structured JSON completion."""

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

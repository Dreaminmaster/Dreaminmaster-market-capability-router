"""Configuration for the v0.2 model adapter.

Precedence: CLI flags > environment variables > defaults.

No secrets are persisted or printed by this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMConfig:
    """Resolved LLM configuration. Empty means 'not configured'."""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 1

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def mask(self) -> dict[str, object]:
        """Return a safe representation for logging (no secrets)."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }

    def __repr__(self) -> str:
        return repr(self.mask())


def resolve_config(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
) -> LLMConfig:
    """Resolve LLM configuration from CLI-like kwargs and environment variables.

    Precedence is highest-first: explicit kwargs, then env vars, then defaults.
    API key resolution follows env-var convention and never appears in logs.
    """
    resolved_base = base_url or os.getenv("MCR_LLM_BASE_URL", "")
    resolved_key = api_key or os.getenv("MCR_LLM_API_KEY", "")
    resolved_model = model or os.getenv("MCR_LLM_MODEL", "")

    try:
        resolved_timeout = float(
            timeout_seconds if timeout_seconds is not None
            else os.getenv("MCR_LLM_TIMEOUT_SECONDS", "30.0")
        )
    except (ValueError, TypeError):
        resolved_timeout = 30.0

    try:
        resolved_retries = int(
            max_retries if max_retries is not None
            else os.getenv("MCR_LLM_MAX_RETRIES", "1")
        )
    except (ValueError, TypeError):
        resolved_retries = 1

    return LLMConfig(
        base_url=resolved_base,
        api_key=resolved_key,
        model=resolved_model,
        timeout_seconds=resolved_timeout,
        max_retries=resolved_retries,
    )

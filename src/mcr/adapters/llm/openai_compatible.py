"""OpenAI-compatible chat-completions adapter.

Supports hosted providers, LM Studio, and local endpoints.
Uses only Python standard library (no external HTTP deps).

Key features:
- Configurable base URL and model
- Optional API key (local endpoints may not require one)
- Mandatory timeout
- Bounded retry for transport errors only
- Never logs or returns API keys
- No retry on auth errors or invalid schemas
"""

from __future__ import annotations

import json
import http.client
import time
import urllib.parse
import urllib.error
from typing import Any

from .base import LLMResponse


class LLMAdapterError(RuntimeError):
    """Raised for transport-level failures."""

    def __init__(self, message: str, *, cause: BaseException | None = None):
        super().__init__(message)
        self.cause = cause


class LLMAuthError(LLMAdapterError):
    """Raised on authentication (401/403) errors."""


class LLMTimeoutError(LLMAdapterError):
    """Raised when the request exceeds the configured timeout."""


class LLMResponseError(LLMAdapterError):
    """Raised when the response cannot be parsed to valid JSON."""


class OpenAICompatibleAdapter:
    """Standard-library HTTP adapter for OpenAI-compatible endpoints."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ):
        if not base_url:
            raise ValueError("base_url is required")
        if not model:
            raise ValueError("model is required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    # ── public API ───────────────────────────────────────────────────────

    def complete_json(
        self,
        *,
        system: str,
        user_payload: dict[str, object],
        schema: dict[str, object],
        timeout_seconds: float | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        timeout = timeout_seconds or self.timeout_seconds
        warnings: list[str] = []

        # Build the request body
        body = self._build_request(system, user_payload, schema, max_tokens)
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        last_error: BaseException | None = None
        for attempt in range(self.max_retries + 1):
            try:
                raw_text, latency_ms = self._send(body_bytes, timeout)
                parsed = self._parse(raw_text)
                return LLMResponse(
                    provider="openai_compatible",
                    model=self.model,
                    raw_text=raw_text,
                    parsed=parsed,
                    latency_ms=latency_ms,
                    warnings=warnings,
                )
            except LLMAuthError:
                raise  # Never retry auth errors
            except LLMTimeoutError as exc:
                last_error = exc
            except LLMResponseError as exc:
                last_error = exc
                # Don't retry if we got a valid HTTP response but bad JSON
                if "Unable to parse" in str(exc):
                    break
            except LLMAdapterError as exc:
                last_error = exc

            if attempt < self.max_retries:
                warnings.append(f"Retry {attempt + 1}/{self.max_retries}: {last_error}")

        # All retries exhausted — return failure response
        status = _classify_error(last_error)
        return LLMResponse(
            provider="openai_compatible",
            model=self.model,
            latency_ms=0.0,
            warnings=warnings + [f"Call failed: {type(status)}"],
        )

    # ── internals ─────────────────────────────────────────────────────────

    def _build_request(
        self,
        system: str,
        user_payload: dict[str, object],
        schema: dict[str, object],
        max_tokens: int,
    ) -> dict[str, object]:
        messages: list[dict[str, object]] = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "mcr_analysis",
                    "strict": True,
                    "schema": schema,
                },
            },
        }

    def _send(self, body_bytes: bytes, timeout: float) -> tuple[str, float]:
        parsed_url = urllib.parse.urlparse(self.base_url + "/chat/completions")
        t0 = time.monotonic()

        try:
            if parsed_url.scheme == "https":
                conn = http.client.HTTPSConnection(
                    parsed_url.hostname or "localhost",
                    parsed_url.port or 443,
                    timeout=timeout,
                )
            else:
                conn = http.client.HTTPConnection(
                    parsed_url.hostname or "localhost",
                    parsed_url.port or 80,
                    timeout=timeout,
                )

            path = parsed_url.path or "/chat/completions"
            if parsed_url.query:
                path += "?" + parsed_url.query

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            }
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            conn.request("POST", path, body=body_bytes, headers=headers)
            response = conn.getresponse()
            status = response.status
            raw = response.read().decode("utf-8")

            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            if status in (401, 403):
                raise LLMAuthError(f"Authentication failed (HTTP {status})")

            if status != 200:
                # Try to extract error detail from response
                detail = ""
                try:
                    error_body = json.loads(raw)
                    detail = error_body.get("error", {}).get("message", raw[:200])
                except Exception:
                    detail = raw[:200]
                raise LLMAdapterError(
                    f"HTTP {status}: {detail}" if detail else f"HTTP {status}"
                )

            return raw, latency_ms

        except (LLMAuthError, LLMAdapterError):
            raise
        except http.client.HTTPException as exc:
            raise LLMAdapterError(str(exc), cause=exc)
        except TimeoutError as exc:
            raise LLMTimeoutError("Request timed out", cause=exc)
        except OSError as exc:
            raise LLMAdapterError(f"Connection error: {exc}", cause=exc)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _parse(self, raw_text: str) -> dict[str, object]:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"Unable to parse model response as JSON: {exc}",
                cause=exc,
            )

        # OpenAI chat completion shape
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError("No choices in response")

        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise LLMResponseError("Invalid message in response")

        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("Empty content in response")

        try:
            return json.loads(content)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"Unable to parse content as JSON: {exc}",
                cause=exc,
            )


def _classify_error(exc: BaseException | None) -> str:
    if exc is None:
        return "unknown"
    if isinstance(exc, LLMAuthError):
        return "auth_error"
    if isinstance(exc, LLMTimeoutError):
        return "timeout"
    if isinstance(exc, LLMResponseError):
        if "Unable to parse" in str(exc):
            return "invalid_json"
        return "response_error"
    return "connection_error"

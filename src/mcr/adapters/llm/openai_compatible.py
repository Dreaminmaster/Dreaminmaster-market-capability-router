"""OpenAI-compatible adapter. Always returns structured LLMResponse."""

from __future__ import annotations

import json
import http.client
import time
import urllib.parse
from typing import Any

from .base import (
    LLMResponse,
    STATUS_OK,
    STATUS_TIMEOUT,
    STATUS_CONNECTION_ERROR,
    STATUS_AUTH_ERROR,
    STATUS_HTTP_ERROR,
    STATUS_INVALID_JSON,
    STATUS_RESPONSE_TOO_LARGE,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB

RETRYABLE_HTTP = {429, 502, 503, 504}
RETRYABLE_EXCEPTIONS = (TimeoutError, ConnectionError, OSError, http.client.HTTPException)


class OpenAICompatibleAdapter:
    def __init__(
        self, base_url: str, model: str, api_key: str = "",
        timeout_seconds: float = 30.0, max_retries: int = 1,
    ):
        if not base_url:
            raise ValueError("base_url required")
        if not model:
            raise ValueError("model required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def complete_json(
        self, *, system: str, user_payload: dict[str, object],
        schema: dict[str, object], timeout_seconds: float | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        timeout = timeout_seconds or self.timeout_seconds
        warnings: list[str] = []
        body = self._build_request(system, user_payload, schema, max_tokens)
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            try:
                raw_text, latency_ms = self._send(body_bytes, timeout)
                parsed = self._parse(raw_text)
                return LLMResponse(
                    provider="openai_compatible", model=self.model,
                    raw_text=raw_text, parsed=parsed, latency_ms=latency_ms,
                    warnings=warnings, status=STATUS_OK,
                )
            except _RetryableServerError as exc:
                attempt_num = attempt + 1
                if attempt_num <= self.max_retries:
                    warnings.append(f"Retry {attempt_num}/{self.max_retries}: {exc}")
                    continue
                return LLMResponse(
                    provider="openai_compatible", model=self.model,
                    warnings=warnings + [str(exc)],
                    status=exc.status, error_type=exc.error_type,
                    http_status=exc.http_status,
                )
            except _NonRetryable as exc:
                return LLMResponse(
                    provider="openai_compatible", model=self.model,
                    warnings=warnings + [str(exc)],
                    status=exc.status, error_type=exc.error_type,
                    http_status=exc.http_status,
                )
            except Exception as exc:
                is_retryable = isinstance(exc, RETRYABLE_EXCEPTIONS)
                attempt_num = attempt + 1
                if is_retryable and attempt_num <= self.max_retries:
                    warnings.append(f"Retry {attempt_num}/{self.max_retries}: {exc}")
                    continue
                status = _map_exc(exc)
                return LLMResponse(
                    provider="openai_compatible", model=self.model,
                    warnings=warnings + [str(exc)],
                    status=status[0], error_type=status[1],
                )

        # Should not reach here, but fallback
        return LLMResponse(
            provider="openai_compatible", model=self.model,
            warnings=warnings, status=STATUS_CONNECTION_ERROR,
            error_type="exhausted_retries",
        )

    def _build_request(self, system, user_payload, schema, max_tokens):
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "mcr_analysis", "strict": True, "schema": schema},
            },
        }

    def _send(self, body_bytes: bytes, timeout: float) -> tuple[str, float]:
        parsed_url = urllib.parse.urlparse(self.base_url + "/chat/completions")
        t0 = time.monotonic()
        conn = None
        try:
            if parsed_url.scheme == "https":
                conn = http.client.HTTPSConnection(
                    parsed_url.hostname or "localhost", parsed_url.port or 443, timeout=timeout)
            else:
                conn = http.client.HTTPConnection(
                    parsed_url.hostname or "localhost", parsed_url.port or 80, timeout=timeout)
            path = parsed_url.path or "/chat/completions"
            if parsed_url.query:
                path += "?" + parsed_url.query
            headers = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            conn.request("POST", path, body=body_bytes, headers=headers)
            response = conn.getresponse()
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace")
            if len(response.read(1)) > 0:
                raise _NonRetryable(STATUS_RESPONSE_TOO_LARGE, "response_too_large",
                                    "Response body exceeds limit", http_status=status)
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            if status in (401, 403):
                raise _NonRetryable(STATUS_AUTH_ERROR, "auth_error",
                                    f"HTTP {status}", http_status=status)
            if status == 400:
                raise _NonRetryable(STATUS_HTTP_ERROR, "http_error",
                                    f"HTTP 400 Bad Request", http_status=status)
            if status == 404:
                raise _NonRetryable(STATUS_HTTP_ERROR, "http_error",
                                    f"HTTP 404 Not Found", http_status=status)
            if status in (429, 502, 503, 504):
                raise _RetryableServerError(STATUS_HTTP_ERROR, "http_error",
                                            f"HTTP {status}", http_status=status)
            if status >= 500:
                raise _RetryableServerError(STATUS_HTTP_ERROR, "http_error",
                                            f"HTTP {status}", http_status=status)
            if status != 200:
                raise _NonRetryable(STATUS_HTTP_ERROR, "http_error",
                                    f"HTTP {status}", http_status=status)
            return raw, latency_ms
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _parse(self, raw_text: str) -> dict[str, object]:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            raise _NonRetryable(STATUS_INVALID_JSON, "invalid_json", "Response is not valid JSON")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise _NonRetryable(STATUS_INVALID_JSON, "invalid_json", "No choices in response")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise _NonRetryable(STATUS_INVALID_JSON, "invalid_json", "Invalid message structure")
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise _NonRetryable(STATUS_INVALID_JSON, "invalid_json", "Empty content")
        try:
            return json.loads(content)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            raise _NonRetryable(STATUS_INVALID_JSON, "invalid_json", "Content is not valid JSON")


# ── Internal exception helpers ─────────────────────────────────────

class _NonRetryable(Exception):
    def __init__(self, status: str, error_type: str, message: str, http_status: int | None = None):
        super().__init__(message)
        self.status = status
        self.error_type = error_type
        self.http_status = http_status


class _RetryableServerError(_NonRetryable):
    pass


def _map_exc(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, TimeoutError):
        return STATUS_TIMEOUT, "timeout"
    if isinstance(exc, (ConnectionError, OSError)):
        return STATUS_CONNECTION_ERROR, "connection_error"
    if isinstance(exc, http.client.HTTPException):
        return STATUS_CONNECTION_ERROR, "http_exception"
    return STATUS_CONNECTION_ERROR, "unknown"

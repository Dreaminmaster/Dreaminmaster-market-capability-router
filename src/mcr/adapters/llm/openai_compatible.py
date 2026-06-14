"""OpenAI-compatible chat-completions adapter with proper status classification.

Uses only Python standard library.
"""

from __future__ import annotations

import json
import http.client
import time
import urllib.parse
from typing import Any

from .base import LLMResponse


class LLMAdapterError(RuntimeError):
    def __init__(self, message: str, *, cause: BaseException | None = None):
        super().__init__(message)
        self.cause = cause


class LLMAuthError(LLMAdapterError):
    pass


class LLMTimeoutError(LLMAdapterError):
    pass


class LLMResponseError(LLMAdapterError):
    pass


class LLMHttpError(LLMAdapterError):
    """Non-retryable HTTP client error (4xx except 429)."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class LLMServerError(LLMAdapterError):
    """Potentially retryable server error (5xx)."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


RETRYABLE_HTTP = {429, 502, 503, 504}
NON_RETRYABLE_HTTP = {400, 401, 403, 404}


MODEL_STATUS_NOT_CONFIGURED = "not_configured"
MODEL_STATUS_OK = "ok"
MODEL_STATUS_TIMEOUT = "timeout"
MODEL_STATUS_CONNECTION_ERROR = "connection_error"
MODEL_STATUS_AUTH_ERROR = "auth_error"
MODEL_STATUS_HTTP_ERROR = "http_error"
MODEL_STATUS_INVALID_JSON = "invalid_json"
MODEL_STATUS_SCHEMA_ERROR = "schema_error"
MODEL_STATUS_RESPONSE_TOO_LARGE = "response_too_large"
MODEL_STATUS_PROMPT_INJECTION = "prompt_injection_warning"


def _classify_error(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    if isinstance(exc, LLMAuthError):
        return MODEL_STATUS_AUTH_ERROR
    if isinstance(exc, LLMTimeoutError):
        return MODEL_STATUS_TIMEOUT
    if isinstance(exc, LLMResponseError):
        if "Unable to parse" in str(exc):
            return MODEL_STATUS_INVALID_JSON
        return MODEL_STATUS_INVALID_JSON
    if isinstance(exc, LLMHttpError):
        return MODEL_STATUS_HTTP_ERROR
    if isinstance(exc, LLMServerError):
        return MODEL_STATUS_HTTP_ERROR
    return MODEL_STATUS_CONNECTION_ERROR


class OpenAICompatibleAdapter:
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
        body = self._build_request(system, user_payload, schema, max_tokens)
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        last_error: BaseException | None = None
        attempt: int = 0
        while attempt <= self.max_retries:
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
            except (LLMAuthError, LLMHttpError):
                raise  # Never retry
            except LLMResponseError:
                # Invalid JSON from a valid HTTP response — don't retry
                last_error = _current_exc()
                break
            except (LLMTimeoutError, LLMServerError) as exc:
                last_error = exc
                attempt += 1
                if attempt <= self.max_retries:
                    warnings.append(f"Retry {attempt}/{self.max_retries}: {exc}")
            except LLMAdapterError as exc:
                last_error = exc
                attempt += 1
                if attempt <= self.max_retries:
                    warnings.append(f"Retry {attempt}/{self.max_retries}: {exc}")

        status = _classify_error(last_error) or "unknown"
        return LLMResponse(
            provider="openai_compatible",
            model=self.model,
            latency_ms=0.0,
            warnings=warnings + [f"Call failed: {status}"],
        )

    def _build_request(
        self, system: str, user_payload: dict[str, object],
        schema: dict[str, object], max_tokens: int,
    ) -> dict[str, object]:
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
        conn = None
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
            if status in NON_RETRYABLE_HTTP:
                raise LLMHttpError(f"HTTP {status}", status)
            if status in RETRYABLE_HTTP:
                raise LLMServerError(f"HTTP {status}", status)
            if status >= 500:
                raise LLMServerError(f"HTTP {status}", status)
            if status != 200:
                detail = ""
                try:
                    error_body = json.loads(raw)
                    detail = error_body.get("error", {}).get("message", raw[:200])
                except Exception:
                    detail = raw[:200]
                raise LLMAdapterError(f"HTTP {status}: {detail}" if detail else f"HTTP {status}")
            return raw, latency_ms
        except (LLMAuthError, LLMHttpError, LLMServerError, LLMResponseError, LLMAdapterError):
            raise
        except TimeoutError as exc:
            raise LLMTimeoutError("Request timed out", cause=exc)
        except http.client.HTTPException as exc:
            raise LLMAdapterError(str(exc), cause=exc)
        except OSError as exc:
            raise LLMAdapterError(f"Connection error: {exc}", cause=exc)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _parse(self, raw_text: str) -> dict[str, object]:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(f"Unable to parse model response as JSON: {exc}", cause=exc)
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
            raise LLMResponseError(f"Unable to parse content as JSON: {exc}", cause=exc)


def _current_exc() -> BaseException | None:
    import sys
    return sys.exc_info()[1]

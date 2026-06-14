"""Validate and redact data before model enrichment (recursive redaction)."""

from __future__ import annotations

import re
from typing import Any

_REDACTION_RULES: list[tuple[re.Pattern, str]] = []


def _add(pattern_str: str, label: str, flags: int = 0) -> None:
    _REDACTION_RULES.append((re.compile(pattern_str, flags), label))


_add(r"\b(\d{4,8})\s*(?:验证码|码)\b", "[验证码已脱敏]")
_add(r"(verification code[s]?):\s*\S+", r"\1: [redacted]", re.IGNORECASE)
_add(r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "[身份证号已脱敏]")
_add(r"\b\d{13,19}\b", "[银行卡号已脱敏]")
_add(r"\S+@\S+\.\S{2,}", "[邮箱已脱敏]")
_add(r"\b1[3-9]\d{9}\b", "[手机号已脱敏]")
_add(
    r"[\"']?(?:password|passwd|pwd|secret|token|api_key)[\"']?\s*[:=]\s*[\"']?\S+[\"']?",
    "[凭据已脱敏]",
    re.IGNORECASE,
)


def redact(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    result = text
    for pattern, label in _REDACTION_RULES:
        if pattern.search(result):
            warnings.append(label)
            result = pattern.sub(label, result)
    return result, _uniq(warnings)


def redact_recursive(obj: Any, _seen: set | None = None) -> tuple[Any, list[str]]:
    """Recursively redact all strings in nested dict/list/tuple/string.

    Returns (redacted_obj, warnings).
    """
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return obj, []
    _seen.add(obj_id)

    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        all_warnings: list[str] = []
        result = {}
        for k, v in obj.items():
            redacted_val, warnings = redact_recursive(v, _seen)
            all_warnings.extend(warnings)
            result[k] = redacted_val
        return result, _uniq(all_warnings)
    if isinstance(obj, (list, tuple)):
        all_warnings = []
        result = []
        for v in obj:
            redacted_val, warnings = redact_recursive(v, _seen)
            all_warnings.extend(warnings)
            result.append(redacted_val)
        return result, _uniq(all_warnings)
    return obj, []


def redact_dict(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Shallow redact for backward compatibility — prefer redact_recursive."""
    return redact_recursive(data)  # type: ignore[return-value]


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

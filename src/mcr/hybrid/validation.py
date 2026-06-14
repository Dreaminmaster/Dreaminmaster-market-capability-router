"""Validate and redact data before model enrichment."""

from __future__ import annotations

import re
from typing import Any

# ── compiled redaction patterns ────────────────────────────────────────────

# Each element: (compiled_pattern, replacement_label)
_REDACTION_RULES: list[tuple[re.Pattern, str]] = []

def _add(pattern_str: str, label: str, flags: int = 0) -> None:
    _REDACTION_RULES.append((re.compile(pattern_str, flags), label))

# Verification codes (4-8 digits followed by verification-code hint)
_add(r"\b(\d{4,8})\s*(?:验证码|码)\b", "[验证码已脱敏]")

# English verification-code mentions
_add(r"(verification code[s]?):\s*\S+", r"\1: [redacted]", re.IGNORECASE)

# Chinese identity numbers (18 digits or 17 digits + X)
_add(r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "[身份证号已脱敏]")

# Bank cards (13-19 digits)
_add(r"\b\d{13,19}\b", "[银行卡号已脱敏]")

# Email addresses
_add(r"\S+@\S+\.\S{2,}", "[邮箱已脱敏]")

# Chinese mobile phone numbers (1[3-9] × 9 digits)
_add(r"\b1[3-9]\d{9}\b", "[手机号已脱敏]")

# Password-like fields in key=value or JSON-ish strings
_add(
    r"[\"']?(?:password|passwd|pwd|secret|token|api_key)[\"']?\s*[:=]\s*[\"']?\S+[\"']?",
    "[凭据已脱敏]",
    re.IGNORECASE,
)


def redact(text: str) -> tuple[str, list[str]]:
    """Redact sensitive data from a string.

    Returns (redacted_text, warnings) — warnings describe what was
    redacted, NOT the original value.
    """
    warnings: list[str] = []
    result = text
    for pattern, label in _REDACTION_RULES:
        if pattern.search(result):
            warnings.append(label)
            result = pattern.sub(label, result)
    return result, _uniq(warnings)


def redact_dict(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Redact sensitive data from a dictionary (shallow for v0.2)."""
    all_warnings: list[str] = []
    result = dict(data)
    for key, value in list(result.items()):
        if isinstance(value, str):
            redacted_val, warnings = redact(value)
            result[key] = redacted_val
            all_warnings.extend(warnings)
    return result, _uniq(all_warnings)


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

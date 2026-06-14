"""Validate and redact data before model enrichment."""

from __future__ import annotations

import re
from typing import Any

# Heuristic patterns — not 100% coverage, but safe for v0.2.
# The goal is to prevent obviously sensitive tokens from reaching an LLM.
_PATTERNS: list[tuple[str, str]] = [
    # Verification codes (4-8 digits)
    (r"\b(\d{4,8})\s*(?:验证码|码)\b", "[验证码已脱敏]"),
    (r"\b(verification code[s]?):\s*\S+", r"\1: [redacted]", re.IGNORECASE),
    # Chinese identity numbers (18 digits or 17 digits + X)
    (r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "[身份证号已脱敏]"),
    # Bank cards (13-19 digits)
    (r"\b\d{13,19}\b", "[银行卡号已脱敏]"),
    # Email addresses
    (r"\S+@\S+\.\S{2,}", "[邮箱已脱敏]"),
    # Phone-like sequences (Chinese mobile: 1[3-9] x 9 more digits)
    (r"\b1[3-9]\d{9}\b", "[手机号已脱敏]"),
    # Password-like fields in JSON or key-value
    (r#"["']?(?:password|passwd|pwd|secret|token|api_key)["']?\s*[:=]\s*["']?\S+["']?"#, "[凭据已脱敏]", re.IGNORECASE),
]

_compiled = [(re.compile(pat, flags | re.MULTILINE) if isinstance(flags, int) else re.compile(pat, flags), label)
             for pat, label, *rest in _PATTERNS
             for flags in (rest[0] if rest else re.MULTILINE)]


def redact(text: str) -> tuple[str, list[str]]:
    """Redact sensitive data from a string.

    Returns (redacted_text, warnings) — warnings describe what was redacted, NOT the original value.
    """
    warnings: list[str] = []
    result = text
    for pattern, label in _compiled:
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
            redacted, warnings = redact(value)
            result[key] = redacted
            all_warnings.extend(warnings)
    return result, _uniq(all_warnings)


def _uniq(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

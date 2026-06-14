"""Validate and redact data recursively. Strings first, then containers.

Supports Chinese password patterns like 密码是abc123, 密码: abc123, etc.
"""

from __future__ import annotations

import re
from typing import Any

_REDACTION_RULES: list[tuple[re.Pattern, str]] = []


def _add(pattern_str: str, label: str, flags: int = 0) -> None:
    _REDACTION_RULES.append((re.compile(pattern_str, flags), label))


# English credential patterns
_add(r"(verification code[s]?):\s*\S+", r"\1: [redacted]", re.IGNORECASE)
_add(
    r"[\"']?(?:password|passwd|pwd|secret|token|api_key)[\"']?\s*[:=]\s*[\"']?\S+[\"']?",
    "[凭据已脱敏]", re.IGNORECASE,
)

# Chinese password patterns (must come before numeric/identity to avoid false matches)
_cn_password_prefix = r"(?:密码|口令|登录密码|支付密码|验证码|短信码|验证)\s*[:：是]\s*"
_add(rf"{_cn_password_prefix}\S+", "[凭据已脱敏]")

# Verification codes — standalone digits with Chinese hint
_add(r"\b(\d{4,8})\s*(?:验证码|码|短信码)\b", "[验证码已脱敏]")

# Identity / bank / email / phone (after password, so passwords aren't mistaken)
_add(r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b", "[身份证号已脱敏]")
_add(r"\b\d{13,19}\b", "[银行卡号已脱敏]")
_add(r"\S+@\S+\.\S{2,}", "[邮箱已脱敏]")
_add(r"\b1[3-9]\d{9}\b", "[手机号已脱敏]")


def redact(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    result = text
    for pattern, label in _REDACTION_RULES:
        if pattern.search(result):
            warnings.append(label)
            result = pattern.sub(label, result)
    return result, _uniq(warnings)


def redact_recursive(obj: Any, _seen: set | None = None) -> tuple[Any, list[str]]:
    if isinstance(obj, str):
        return redact(obj)
    if not isinstance(obj, (dict, list, tuple)):
        return obj, []
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return obj, []
    _seen.add(obj_id)
    if isinstance(obj, dict):
        all_warnings: list[str] = []
        result = {}
        for k, v in obj.items():
            rv, warnings = redact_recursive(v, _seen)
            all_warnings.extend(warnings)
            result[k] = rv
        return result, _uniq(all_warnings)
    all_warnings = []
    result = []
    for v in obj:
        rv, warnings = redact_recursive(v, _seen)
        all_warnings.extend(warnings)
        result.append(rv)
    tp = type(obj)
    return tp(result), _uniq(all_warnings)


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

"""Lightweight trigger gate: rejects clearly AI-only tasks."""

from __future__ import annotations

import re

# Tasks clearly completable by AI with no real-world capability routing
SIMPLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Purely text manipulation
    (re.compile(r"改.*通顺|润色|改.*流畅|改.*自然"), "rewriting"),
    (re.compile(r"整理.*清楚|整理.*文字"), "text organizing"),
    # Translation WITHOUT qualification context
    (re.compile(r"^翻译(.{0,10})$|帮我翻译(.{0,8})$|^(translate|请翻译)"), "bare translation"),
    # Summarization
    (re.compile(r"摘要|总结|归纳|概括"), "summarization"),
    # Pure text generation
    (re.compile(r"生成.*文字|写.*文章|写.*文案|生成.*文案"), "text generation"),
    # Calculation
    (re.compile(r"计算|算一下|帮我算"), "calculation"),
]

# Context that upgrades a bare keyword to capability routing
QUALIFYING_CONTEXT: list[re.Pattern] = [
    re.compile(r"公证|法律|有资质|专业人员|认证翻译|certified|notariz"),
    re.compile(r"代办|外包|找人|marketplace|闲鱼|淘宝|service"),
]


def should_use_capability_router(text: str) -> bool:
    """Return False ONLY if text is clearly AI-only. If unsure, return True."""
    if not text or not text.strip():
        return False

    lower = text.lower()

    # Check qualifying context first — if present, always route
    for pattern in QUALIFYING_CONTEXT:
        if pattern.search(lower):
            return True

    # Check simple patterns
    for pattern, _label in SIMPLE_PATTERNS:
        if pattern.search(lower):
            return False

    return True

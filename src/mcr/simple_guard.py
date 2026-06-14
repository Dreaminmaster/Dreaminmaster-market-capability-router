"""Lightweight deterministic trigger gate for simple tasks.

Prevents unnecessary MCR or model invocation for tasks that are clearly
AI-only or non-capability-related.
"""

from __future__ import annotations

import re

# Tasks that are purely text manipulation — no real-world capability routing needed
SIMPLE_ACTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"改.*通顺|润色|改.*流畅|改.*自然"),
    re.compile(r"翻译|translate"),
    re.compile(r"摘要|总结|归纳|概括"),
    re.compile(r"生成.*文字|写.*文章|写.*文案|生成.*文案"),
    re.compile(r"计算|算一下|帮我算"),
    re.compile(r"整理.*清楚|整理.*文字"),
    re.compile(r"rephrase|rewrite|summarize|generate.*text"),
]

# Requests that clearly have no friction signals for capability routing
MIN_FRICTION_SCORE_THRESHOLD = 0.3


def should_use_capability_router(text: str) -> bool:
    """Return True if text warrants capability routing (not a simple task).

    Simple text manipulation (rewriting, translation, summarization, generation)
    returns False to avoid unnecessary routing or model calls.
    """
    if not text or not text.strip():
        return False

    lower = text.lower()

    for pattern in SIMPLE_ACTION_PATTERNS:
        if pattern.search(lower):
            return False

    return True


def should_use_model(text: str) -> bool:
    """Return True if model enrichment is potentially useful.

    Simple tasks always return False.
    For v0.2, identical to should_use_capability_router.
    """
    return should_use_capability_router(text)

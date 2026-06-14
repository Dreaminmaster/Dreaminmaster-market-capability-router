"""Lightweight trigger gate: rejects clearly AI-only tasks."""

from __future__ import annotations

import re

# Tasks clearly completable by AI with no real-world capability routing
SIMPLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Pure rewriting without capability context
    (re.compile(r"改.*通顺|润色(?!.*(?:审核|报价|合同|律师|造价员|判断|找))|改.*流畅|改.*自然"), "rewriting"),
    (re.compile(r"整理.*清楚|整理.*文字"), "text organizing"),
    # Bare translation without qualifying context
    (re.compile(r"翻译(?:一下|这个|那个|这段|句子|文字|一句话|一句|一篇|这段话)?[。，；.!?]*$"), "bare translation"),
    # Pure summarization without follow-up
    (re.compile(r"帮.*总结(?!.*(?:报价|合同|判断|找|审核|律师|造价))|帮.*摘要|帮.*归纳|帮.*概括"), "summarization"),
    # Pure generation
    (re.compile(r"生成.*文字|写.*文章|写.*文案|生成.*文案"), "text generation"),
    # Bare calculation
    (re.compile(r"帮.*算(?!.*(?:申诉|律师|找|判断))|计算一下"), "calculation"),
]

QUALIFYING_CONTEXT: list[re.Pattern] = [
    re.compile(r"公证|法律|有资质|专业人员|认证翻译|certified|notariz"),
    re.compile(r"代办|外包|找人|marketplace|闲鱼|淘宝|service"),
    re.compile(r"造价员|审核|合同|律师|复核|申诉|监理"),
    re.compile(r"判断.*(?:找|购买|外包|需要)"),
    re.compile(r"(?:翻译|总结|计算).*(?:找|判断|审核|申诉|律师|造价)"),  # compound
]


def should_use_capability_router(text: str) -> bool:
    """Return False ONLY if text is clearly AI-only."""
    if not text or not text.strip():
        return False
    lower = text.lower()

    for pattern in QUALIFYING_CONTEXT:
        if pattern.search(lower):
            return True

    for pattern, _label in SIMPLE_PATTERNS:
        if pattern.search(lower):
            return False

    return True

"""Versioned structured-output schemas for the v0.2 model adapter."""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "0.2"

VALID_FRICTION_TYPES = {"knowledge", "diagnosis", "skill", "channel", "execution", "verification"}
VALID_ROUTES = {"AI", "TOOL", "SELF", "PROFESSIONAL", "MARKET", "OFFICIAL"}
VALID_SENSITIVITY = {"low", "medium", "high"}

# Limit oversized arrays from a model
MAX_ARRAY_LENGTH = 60
MAX_STRING_LENGTH = 500

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "schema_version",
        "real_goal",
        "friction_hypotheses",
        "task_hypotheses",
        "profession_terms",
        "service_terms",
        "query_terms",
        "unknown_dialect_hypotheses",
        "warnings",
    ],
    "properties": {
        "schema_version": {"type": "string", "const": "0.2"},
        "real_goal": {"type": "string", "maxLength": MAX_STRING_LENGTH},
        "friction_hypotheses": {
            "type": "array",
            "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["type", "confidence", "evidence", "uncertainty"],
                "properties": {
                    "type": {"type": "string", "enum": sorted(VALID_FRICTION_TYPES)},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "uncertainty": {"type": "string"},
                },
            },
        },
        "task_hypotheses": {
            "type": "array",
            "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["title", "expected_deliverable", "suggested_routes", "requires_user_action", "sensitivity"],
                "properties": {
                    "title": {"type": "string", "maxLength": MAX_STRING_LENGTH},
                    "expected_deliverable": {"type": "string", "maxLength": MAX_STRING_LENGTH},
                    "suggested_routes": {
                        "type": "array",
                        "items": {"type": "string", "enum": sorted(VALID_ROUTES)},
                    },
                    "requires_user_action": {"type": "boolean"},
                    "sensitivity": {"type": "string", "enum": sorted(VALID_SENSITIVITY)},
                },
            },
        },
        "profession_terms": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ARRAY_LENGTH},
        "service_terms": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ARRAY_LENGTH},
        "query_terms": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ARRAY_LENGTH},
        "unknown_dialect_hypotheses": {
            "type": "array",
            "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["term", "possible_meanings", "confidence", "evidence_required"],
                "properties": {
                    "term": {"type": "string"},
                    "possible_meanings": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "evidence_required": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ARRAY_LENGTH},
    },
}

# Quick structural sanity checks that catch obviously malicious payloads.
_INJECTION_PATTERNS = [
    re.compile(r"<\|?im_start\|?>", re.IGNORECASE),
    re.compile(r"<\|?im_end\|?>", re.IGNORECASE),
    re.compile(r"\\n\\nSystem:", re.IGNORECASE),
    re.compile(r"Ignore (all )?previous instructions", re.IGNORECASE),
    re.compile(r"You are now", re.IGNORECASE),
    re.compile(r"New system prompt:", re.IGNORECASE),
]


def validate_schema(payload: dict[str, Any]) -> list[str]:
    """Perform lightweight structural validation. Returns a list of error messages (empty means acceptable)."""
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["Top-level payload must be an object"]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    for key in ("real_goal",):
        val = payload.get(key)
        if not isinstance(val, str) or len(val) > MAX_STRING_LENGTH:
            errors.append(f"{key} must be a short string")

    for section in ("friction_hypotheses", "task_hypotheses", "unknown_dialect_hypotheses"):
        items = payload.get(section, [])
        if not isinstance(items, list):
            errors.append(f"{section} must be an array")
            continue
        if len(items) > MAX_ARRAY_LENGTH:
            errors.append(f"{section} exceeds max length {MAX_ARRAY_LENGTH}")

    # Check for embedded injection patterns in label fields
    _check_injection("real_goal", payload.get("real_goal", ""), errors)

    return errors


def _check_injection(field: str, value: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        return
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            errors.append(f"Prompt injection pattern detected in {field}")


def detect_injection_text(text: str) -> bool:
    """Return True if `text` contains known prompt-injection patterns."""
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)

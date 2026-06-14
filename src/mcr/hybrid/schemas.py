"""Versioned structured-output schemas with deep recursive validation (v0.2 review)."""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "0.2"

VALID_FRICTION_TYPES = {"knowledge", "diagnosis", "skill", "channel", "execution", "verification"}
VALID_ROUTES = {"AI", "TOOL", "SELF", "PROFESSIONAL", "MARKET", "OFFICIAL"}
VALID_SENSITIVITY = {"low", "medium", "high"}

MAX_ARRAY_LENGTH = 60
MAX_STRING_LENGTH = 500

TOP_LEVEL_REQUIRED = [
    "schema_version", "real_goal", "friction_hypotheses", "task_hypotheses",
    "profession_terms", "service_terms", "query_terms", "unknown_dialect_hypotheses", "warnings",
]

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": list(TOP_LEVEL_REQUIRED),
    "properties": {
        "schema_version": {"type": "string", "const": "0.2"},
        "real_goal": {"type": "string", "maxLength": MAX_STRING_LENGTH},
        "friction_hypotheses": {
            "type": "array", "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["type", "confidence", "evidence", "uncertainty"],
                "properties": {
                    "type": {"type": "string", "enum": sorted(VALID_FRICTION_TYPES)},
                    "confidence": {"type": "number"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "uncertainty": {"type": "string"},
                },
            },
        },
        "task_hypotheses": {
            "type": "array", "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["title", "expected_deliverable", "suggested_routes",
                            "requires_user_action", "sensitivity"],
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
            "type": "array", "maxItems": MAX_ARRAY_LENGTH,
            "items": {
                "type": "object",
                "required": ["term", "possible_meanings", "confidence", "evidence_required"],
                "properties": {
                    "term": {"type": "string"},
                    "possible_meanings": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                    "evidence_required": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}, "maxItems": MAX_ARRAY_LENGTH},
    },
}

_INJECTION_PATTERNS = [
    re.compile(r"<\|?im_start\|?>", re.IGNORECASE),
    re.compile(r"<\|?im_end\|?>", re.IGNORECASE),
    re.compile(r"\\n\\nSystem:", re.IGNORECASE),
    re.compile(r"Ignore (all )?previous instructions", re.IGNORECASE),
    re.compile(r"You are now", re.IGNORECASE),
    re.compile(r"New system prompt:", re.IGNORECASE),
]


def _is_number(val: Any) -> bool:
    """True for int/float but NOT bool (since isinstance(True, int)==True)."""
    if isinstance(val, bool):
        return False
    return isinstance(val, (int, float))


def _check_string(val: Any, path: str, errors: list[str]) -> None:
    if not isinstance(val, str):
        errors.append(f"{path}: expected string, got {type(val).__name__}")
    elif len(val) > MAX_STRING_LENGTH:
        errors.append(f"{path}: exceeds max length {MAX_STRING_LENGTH}")


def _check_number(val: Any, path: str, errors: list[str]) -> None:
    if not _is_number(val):
        errors.append(f"{path}: expected number, got {type(val).__name__}")
    elif not (0.0 <= float(val) <= 1.0):
        errors.append(f"{path}: {val} not in [0,1]")


def _check_bool(val: Any, path: str, errors: list[str]) -> None:
    if not isinstance(val, bool):
        errors.append(f"{path}: expected boolean, got {type(val).__name__}")


def _check_str_array(val: Any, path: str, errors: list[str]) -> None:
    if not isinstance(val, list):
        errors.append(f"{path}: expected array, got {type(val).__name__}")
        return
    if len(val) > MAX_ARRAY_LENGTH:
        errors.append(f"{path}: exceeds max length {MAX_ARRAY_LENGTH}")
    for i, item in enumerate(val):
        if not isinstance(item, str):
            errors.append(f"{path}[{i}]: must be string")


def validate_schema(payload: dict[str, Any]) -> list[str]:
    """Recursive deep validation of model output against v0.2 schema."""
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["Top-level payload must be an object"]

    for key in TOP_LEVEL_REQUIRED:
        if key not in payload:
            errors.append(f"Missing required field: {key}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    rg = payload.get("real_goal")
    _check_string(rg, "real_goal", errors)
    if isinstance(rg, str):
        _check_injection("real_goal", rg, errors)

    _validate_frictions(payload.get("friction_hypotheses"), errors)
    _validate_tasks(payload.get("task_hypotheses"), errors)
    _validate_dialects(payload.get("unknown_dialect_hypotheses"), errors)

    for field in ("profession_terms", "service_terms", "query_terms", "warnings"):
        _check_str_array(payload.get(field), field, errors)

    return errors


def _validate_frictions(items: Any, errors: list[str]) -> None:
    if not isinstance(items, list):
        errors.append("friction_hypotheses must be an array")
        return
    if len(items) > MAX_ARRAY_LENGTH:
        errors.append(f"friction_hypotheses exceeds max length {MAX_ARRAY_LENGTH}")
    for i, item in enumerate(items):
        path = f"friction_hypotheses[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue
        for req in ("type", "confidence", "evidence", "uncertainty"):
            if req not in item:
                errors.append(f"{path}: missing required field '{req}'")
        _check_string(item.get("type"), f"{path}.type", errors)
        if isinstance(item.get("type"), str) and item["type"] not in VALID_FRICTION_TYPES:
            errors.append(f"{path}.type: unknown friction type {item['type']!r}")
        _check_number(item.get("confidence"), f"{path}.confidence", errors)
        _check_str_array(item.get("evidence"), f"{path}.evidence", errors)
        _check_string(item.get("uncertainty"), f"{path}.uncertainty", errors)
        if isinstance(item.get("uncertainty"), str):
            _check_injection(f"{path}.uncertainty", item["uncertainty"], errors)


def _validate_tasks(items: Any, errors: list[str]) -> None:
    if not isinstance(items, list):
        errors.append("task_hypotheses must be an array")
        return
    if len(items) > MAX_ARRAY_LENGTH:
        errors.append(f"task_hypotheses exceeds max length {MAX_ARRAY_LENGTH}")
    for i, item in enumerate(items):
        path = f"task_hypotheses[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue
        for req in ("title", "expected_deliverable", "suggested_routes", "requires_user_action", "sensitivity"):
            if req not in item:
                errors.append(f"{path}: missing required field '{req}'")
        _check_string(item.get("title"), f"{path}.title", errors)
        if isinstance(item.get("title"), str):
            _check_injection(f"{path}.title", item["title"], errors)
        _check_string(item.get("expected_deliverable"), f"{path}.expected_deliverable", errors)
        if isinstance(item.get("expected_deliverable"), str):
            _check_injection(f"{path}.expected_deliverable", item["expected_deliverable"], errors)
        routes = item.get("suggested_routes")
        if not isinstance(routes, list):
            errors.append(f"{path}.suggested_routes: must be array")
        else:
            for j, r in enumerate(routes):
                if not isinstance(r, str):
                    errors.append(f"{path}.suggested_routes[{j}]: must be string")
                elif r not in VALID_ROUTES:
                    errors.append(f"{path}.suggested_routes[{j}]: unknown route {r!r}")
        _check_bool(item.get("requires_user_action"), f"{path}.requires_user_action", errors)
        _check_string(item.get("sensitivity"), f"{path}.sensitivity", errors)
        if isinstance(item.get("sensitivity"), str) and item["sensitivity"] not in VALID_SENSITIVITY:
            errors.append(f"{path}.sensitivity: unknown value {item['sensitivity']!r}")


def _validate_dialects(items: Any, errors: list[str]) -> None:
    if not isinstance(items, list):
        errors.append("unknown_dialect_hypotheses must be an array")
        return
    if len(items) > MAX_ARRAY_LENGTH:
        errors.append(f"unknown_dialect_hypotheses exceeds max length {MAX_ARRAY_LENGTH}")
    for i, item in enumerate(items):
        path = f"unknown_dialect_hypotheses[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue
        for req in ("term", "possible_meanings", "confidence", "evidence_required"):
            if req not in item:
                errors.append(f"{path}: missing required field '{req}'")
        _check_string(item.get("term"), f"{path}.term", errors)
        _check_number(item.get("confidence"), f"{path}.confidence", errors)
        _check_str_array(item.get("possible_meanings"), f"{path}.possible_meanings", errors)
        _check_str_array(item.get("evidence_required"), f"{path}.evidence_required", errors)


def _check_injection(field: str, value: str, errors: list[str]) -> None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            errors.append(f"Prompt injection pattern detected in {field}")
            return


def detect_injection_text(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)

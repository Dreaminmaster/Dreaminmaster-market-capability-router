"""Versioned structured-output schemas with deep validation for v0.2."""

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
    "schema_version",
    "real_goal",
    "friction_hypotheses",
    "task_hypotheses",
    "profession_terms",
    "service_terms",
    "query_terms",
    "unknown_dialect_hypotheses",
    "warnings",
]

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": list(TOP_LEVEL_REQUIRED),
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

_INJECTION_PATTERNS = [
    re.compile(r"<\|?im_start\|?>", re.IGNORECASE),
    re.compile(r"<\|?im_end\|?>", re.IGNORECASE),
    re.compile(r"\\n\\nSystem:", re.IGNORECASE),
    re.compile(r"Ignore (all )?previous instructions", re.IGNORECASE),
    re.compile(r"You are now", re.IGNORECASE),
    re.compile(r"New system prompt:", re.IGNORECASE),
]


def _check_field_type(val: Any, expected: str, path: str, errors: list[str]) -> None:
    if expected == "string" and not isinstance(val, str):
        errors.append(f"{path}: expected string, got {type(val).__name__}")
    elif expected == "number" and not isinstance(val, (int, float)):
        errors.append(f"{path}: expected number, got {type(val).__name__}")
    elif expected == "boolean" and not isinstance(val, bool):
        errors.append(f"{path}: expected boolean, got {type(val).__name__}")
    elif expected == "array" and not isinstance(val, list):
        errors.append(f"{path}: expected array, got {type(val).__name__}")
    elif expected == "object" and not isinstance(val, dict):
        errors.append(f"{path}: expected object, got {type(val).__name__}")


def validate_schema(payload: dict[str, Any]) -> list[str]:
    """Recursively validate model output against the v0.2 schema.

    Returns a list of error messages (empty means acceptable).
    """
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["Top-level payload must be an object"]

    # Top-level required fields
    for key in TOP_LEVEL_REQUIRED:
        if key not in payload:
            errors.append(f"Missing required field: {key}")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")

    # real_goal
    rg = payload.get("real_goal")
    if not isinstance(rg, str) or len(rg) > MAX_STRING_LENGTH:
        errors.append("real_goal must be a short string")
    elif isinstance(rg, str):
        _check_injection("real_goal", rg, errors)

    # friction_hypotheses
    _validate_frictions(payload.get("friction_hypotheses"), errors)

    # task_hypotheses
    _validate_tasks(payload.get("task_hypotheses"), errors)

    # unknown_dialect_hypotheses
    _validate_dialects(payload.get("unknown_dialect_hypotheses"), errors)

    # Simple arrays
    for field, item_type in [
        ("profession_terms", "string"),
        ("service_terms", "string"),
        ("query_terms", "string"),
        ("warnings", "string"),
    ]:
        _validate_str_array(payload.get(field), field, errors)

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
        ftype = item.get("type")
        if isinstance(ftype, str) and ftype not in VALID_FRICTION_TYPES:
            errors.append(f"{path}.type: unknown friction type {ftype!r}")
        elif not isinstance(ftype, str):
            errors.append(f"{path}.type: must be a string")
        conf = item.get("confidence")
        if isinstance(conf, str):
            errors.append(f"{path}.confidence: must be a number, got string")
        elif isinstance(conf, (int, float)):
            if not (0.0 <= conf <= 1.0):
                errors.append(f"{path}.confidence: {conf} not in [0,1]")
        ev = item.get("evidence")
        if isinstance(ev, list):
            for j, e in enumerate(ev):
                if not isinstance(e, str):
                    errors.append(f"{path}.evidence[{j}]: must be string")
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
        title = item.get("title")
        if isinstance(title, str):
            if len(title) > MAX_STRING_LENGTH:
                errors.append(f"{path}.title: exceeds max length")
            _check_injection(f"{path}.title", title, errors)
        elif title is not None:
            errors.append(f"{path}.title: must be a string")
        deliverable = item.get("expected_deliverable")
        if isinstance(deliverable, str):
            _check_injection(f"{path}.expected_deliverable", deliverable, errors)
        routes = item.get("suggested_routes")
        if isinstance(routes, list):
            for j, r in enumerate(routes):
                if not isinstance(r, str):
                    errors.append(f"{path}.suggested_routes[{j}]: must be string")
                elif r not in VALID_ROUTES:
                    errors.append(f"{path}.suggested_routes[{j}]: unknown route {r!r}")
        elif routes is not None:
            errors.append(f"{path}.suggested_routes: must be array")
        sens = item.get("sensitivity")
        if isinstance(sens, str) and sens not in VALID_SENSITIVITY:
            errors.append(f"{path}.sensitivity: unknown value {sens!r}")
        if isinstance(item.get("requires_user_action"), str):
            errors.append(f"{path}.requires_user_action: must be boolean, got string")


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
        conf = item.get("confidence")
        if isinstance(conf, str):
            errors.append(f"{path}.confidence: must be a number, got string")
        elif isinstance(conf, (int, float)):
            if not (0.0 <= conf <= 1.0):
                errors.append(f"{path}.confidence: {conf} not in [0,1]")
        meanings = item.get("possible_meanings")
        if isinstance(meanings, list):
            for j, m in enumerate(meanings):
                if not isinstance(m, str):
                    errors.append(f"{path}.possible_meanings[{j}]: must be string")


def _validate_str_array(val: Any, name: str, errors: list[str]) -> None:
    if not isinstance(val, list):
        errors.append(f"{name}: must be an array")
        return
    if len(val) > MAX_ARRAY_LENGTH:
        errors.append(f"{name}: exceeds max length {MAX_ARRAY_LENGTH}")
    for i, item in enumerate(val):
        if not isinstance(item, str):
            errors.append(f"{name}[{i}]: must be string")


def _check_injection(field: str, value: str, errors: list[str]) -> None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            errors.append(f"Prompt injection pattern detected in {field}")
            return


def detect_injection_text(text: str) -> bool:
    """Return True if text contains known prompt-injection patterns."""
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)

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
    if isinstance(rg, str):
        _check_string(rg, "real_goal", errors)
        _check_injection("real_goal", rg, errors)
    elif rg is not None:
        errors.append("real_goal: must be a string")

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
        ftype = item.get("type")
        _check_string(ftype, f"{path}.type", errors)
        if isinstance(ftype, str) and ftype not in VALID_FRICTION_TYPES:
            errors.append(f"{path}.type: unknown friction type {ftype!r}")
        conf = item.get("confidence")
        if conf is not None:
            _check_number(conf, f"{path}.confidence", errors)
        ev = item.get("evidence")
        if ev is not None and not isinstance(ev, list):
            errors.append(f"{path}.evidence: must be array")
        elif isinstance(ev, list):
            for j, e in enumerate(ev):
                if not isinstance(e, str):
                    errors.append(f"{path}.evidence[{j}]: must be string")
        un = item.get("uncertainty")
        if un is not None:
            _check_string(un, f"{path}.uncertainty", errors)
            if isinstance(un, str):
                _check_injection(f"{path}.uncertainty", un, errors)


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
        if title is not None:
            _check_string(title, f"{path}.title", errors)
            if isinstance(title, str):
                _check_injection(f"{path}.title", title, errors)
        deliverable = item.get("expected_deliverable")
        if deliverable is not None:
            _check_string(deliverable, f"{path}.expected_deliverable", errors)
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
        if sens is not None:
            _check_string(sens, f"{path}.sensitivity", errors)
            if isinstance(sens, str) and sens not in VALID_SENSITIVITY:
                errors.append(f"{path}.sensitivity: unknown value {sens!r}")
        ua = item.get("requires_user_action")
        if ua is not None:
            _check_bool(ua, f"{path}.requires_user_action", errors)


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
        term = item.get("term")
        if term is not None:
            _check_string(term, f"{path}.term", errors)
        conf = item.get("confidence")
        if conf is not None:
            _check_number(conf, f"{path}.confidence", errors)
        meanings = item.get("possible_meanings")
        if isinstance(meanings, list):
            for j, m in enumerate(meanings):
                if not isinstance(m, str):
                    errors.append(f"{path}.possible_meanings[{j}]: must be string")
        elif meanings is not None:
            errors.append(f"{path}.possible_meanings: must be array")
        evidence = item.get("evidence_required")
        if isinstance(evidence, list):
            for j, e in enumerate(evidence):
                if not isinstance(e, str):
                    errors.append(f"{path}.evidence_required[{j}]: must be string")
        elif evidence is not None:
            errors.append(f"{path}.evidence_required: must be array")


def _check_injection(field: str, value: str, errors: list[str]) -> None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(value):
            errors.append(f"Prompt injection pattern detected in {field}")
            return


def detect_injection_text(text: str) -> bool:
    if not isinstance(text, str):
        return False
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)

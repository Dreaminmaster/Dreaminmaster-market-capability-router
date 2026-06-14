"""Deterministic hybrid merge — rewritten with per-task SELF/OFFICIAL protection."""

from __future__ import annotations

from typing import Any

from ..models import AnalysisResult, FRICTIONS, ROUTES
from .schemas import detect_injection_text

SOURCE_RULE = "rule"
SOURCE_MODEL = "model"
SOURCE_USER = "user"
SOURCE_SEED = "seed"

STATUS_VERIFIED = "verified"
STATUS_CANDIDATE = "candidate"
STATUS_REJECTED = "rejected"


def merge_analysis(
    rule_result: AnalysisResult,
    model_payload: dict[str, Any] | None,
    model_warnings: list[str] | None = None,
) -> dict[str, Any]:
    enrichment: dict[str, Any] = {
        "attempted": model_payload is not None,
        "applied": False,
        "status": "not_configured",
        "warnings": list(model_warnings or []),
    }
    result = rule_result.to_dict()
    result["model_enrichment"] = enrichment
    result["evidence_trail"] = []
    result["conflicts"] = []

    if model_payload is None:
        return result

    if model_payload.get("schema_version") != "0.2":
        enrichment["status"] = "schema_error"
        enrichment["warnings"].append("Model response schema version mismatch")
        return result

    injection_detected = _check_injection_recursive(model_payload)
    if injection_detected:
        enrichment["status"] = "prompt_injection_warning"
        enrichment["warnings"].append("Prompt injection detected in model output; enrichment skipped")
        return result

    enrichment["applied"] = True
    enrichment["status"] = "ok"

    _merge_real_goal(result, model_payload)
    _merge_frictions(result, model_payload, enrichment)
    _merge_routes(result, model_payload, enrichment)
    _merge_query_terms(result, model_payload)
    _merge_terms(result, model_payload)
    _merge_dialect(result, model_payload)
    _merge_model_warnings(result, model_payload)

    return result


# ── per-field merge helpers ─────────────────────────────────────────────

def _merge_real_goal(result: dict, model: dict) -> None:
    rg = model.get("real_goal")
    if isinstance(rg, str) and rg.strip():
        result.setdefault("evidence_trail", []).append({
            "source": SOURCE_MODEL, "item": "real_goal",
            "status": STATUS_CANDIDATE, "value": rg[:200],
        })


def _merge_frictions(result: dict, model: dict, enrichment: dict) -> None:
    model_frictions = model.get("friction_hypotheses", [])
    if not isinstance(model_frictions, list):
        return
    existing_types = {f["friction_type"] for f in result.get("frictions", [])}
    for mf in model_frictions:
        ftype = mf.get("type")
        if ftype not in FRICTIONS:
            enrichment.setdefault("warnings", []).append(f"Model returned unknown friction type: {ftype}")
            continue
        if ftype in existing_types:
            continue
        result.setdefault("frictions", []).append({
            "friction_type": ftype,
            "score": min(1.0, max(0.0, float(mf.get("confidence", 0.3)))),
            "matched_signals": mf.get("evidence", []),
            "explanation": mf.get("uncertainty", "Model hypothesis — requires confirmation"),
            "source": SOURCE_MODEL,
            "status": STATUS_CANDIDATE,
        })
    result.setdefault("evidence_trail", []).append({"source": SOURCE_MODEL, "item": "friction_hypotheses"})


def _merge_routes(result: dict, model: dict, enrichment: dict) -> None:
    """Per-task route merge. A model task conflicting with a rule-required
    SELF or OFFICIAL on the SAME task is moved to secondary or marked
    as a conflict.  Other tasks are NOT affected."""
    existing_tasks = {r["task"] for r in result.get("routes", [])}
    # Build per-task sensitivity: which existing tasks require SELF/OFFICIAL
    rule_protected: dict[str, str] = {}  # task -> required primary route
    for r in result.get("routes", []):
        if r.get("primary_route") in ("SELF", "OFFICIAL"):
            rule_protected[r["task"]] = r["primary_route"]

    model_tasks = model.get("task_hypotheses", [])
    if not isinstance(model_tasks, list):
        return

    for mt in model_tasks:
        title = (mt.get("title") or "").strip()
        if not title:
            continue
        routes = [r for r in (mt.get("suggested_routes") or []) if r in ROUTES]
        if not routes:
            continue
        primary = routes[0]
        secondaries = list(routes[1:] if len(routes) > 1 else [])

        # Per-task SELF/OFFICIAL conflict: only if this exact task is protected
        conflicts = []
        if title in rule_protected and primary != rule_protected[title]:
            required = rule_protected[title]
            msg = f"Task '{title[:60]}': model suggested {primary} but rules require {required}; keeping {required} as primary, moving model route to secondary"
            enrichment.setdefault("warnings", []).append(msg)
            result.setdefault("conflicts", []).append(msg)
            secondaries = [primary] + secondaries
            primary = required

        result.setdefault("routes", []).append({
            "task": title,
            "primary_route": primary,
            "secondary_routes": secondaries,
            "market_stage": "candidate",
            "confidence": min(1.0, max(0.0, float(mt.get("confidence", 0.5)))),
            "reasons": ["Model hypothesis — requires validation"],
            "human_gate": mt.get("sensitivity") == "high",
            "source": SOURCE_MODEL,
            "status": STATUS_CANDIDATE,
            "expected_deliverable": mt.get("expected_deliverable", ""),
            "requires_user_action": mt.get("requires_user_action", False),
        })
        if conflicts:
            result.setdefault("conflicts", []).extend(conflicts)

    result.setdefault("evidence_trail", []).append({"source": SOURCE_MODEL, "item": "task_hypotheses"})


def _merge_query_terms(result: dict, model: dict) -> None:
    terms = model.get("query_terms", [])
    if isinstance(terms, list) and terms:
        existing = set(result.get("query_lattice", {}).get("combined_queries", []))
        new = [t for t in terms if isinstance(t, str) and t.strip() not in existing][:8]
        if new:
            result.setdefault("query_lattice", {})["query_terms_model"] = new
            result.setdefault("evidence_trail", []).append({
                "source": SOURCE_MODEL, "item": "query_terms",
                "status": STATUS_CANDIDATE,
            })


def _merge_terms(result: dict, model: dict) -> None:
    for field in ("profession_terms", "service_terms"):
        model_terms = model.get(field, [])
        if isinstance(model_terms, list) and model_terms:
            existing = set(result.get("query_lattice", {}).get(field, []))
            new = [t for t in model_terms if isinstance(t, str) and t.strip() not in existing][:8]
            if new:
                result.setdefault("query_lattice", {})[f"{field}_model"] = new
                result.setdefault("evidence_trail", []).append({
                    "source": SOURCE_MODEL, "item": field,
                    "status": STATUS_CANDIDATE,
                })


def _merge_dialect(result: dict, model: dict) -> None:
    dialect = model.get("unknown_dialect_hypotheses", [])
    if not isinstance(dialect, list) or not dialect:
        return
    existing_terms = {d.get("term", "") for d in result.get("dialect_matches", [])}
    new = []
    for d in dialect:
        term = (d.get("term") or "").strip()
        if term and term not in existing_terms:
            new.append({
                "term": term,
                "canonical_concept": "unknown",
                "possible_services": d.get("possible_meanings", []),
                "expression_type": "candidate",
                "risk_level": "unknown",
                "confidence": min(1.0, max(0.0, float(d.get("confidence", 0.3)))),
                "evidence_required": d.get("evidence_required", []),
                "source": SOURCE_MODEL,
                "status": STATUS_CANDIDATE,
            })
    if new:
        result.setdefault("dialect_matches", []).extend(new)
        result.setdefault("evidence_trail", []).append({
            "source": SOURCE_MODEL, "item": "unknown_dialect_hypotheses",
            "status": STATUS_CANDIDATE,
        })


def _merge_model_warnings(result: dict, model: dict) -> None:
    warnings = model.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        result.setdefault("model_enrichment", {}).setdefault("warnings", []).extend(
            [w for w in warnings if isinstance(w, str)]
        )


def _check_injection_recursive(obj: Any, _seen: set | None = None) -> bool:
    """Recursively check all strings in a nested structure for injection."""
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return False
    _seen.add(obj_id)

    if isinstance(obj, str):
        return detect_injection_text(obj)
    if isinstance(obj, dict):
        return any(_check_injection_recursive(v, _seen) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_check_injection_recursive(v, _seen) for v in obj)
    return False

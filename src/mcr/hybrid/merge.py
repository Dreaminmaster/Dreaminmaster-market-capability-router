"""Deterministic hybrid merge: rules always primary, model goes to hypotheses."""

from __future__ import annotations

from typing import Any

from ..models import AnalysisResult, FRICTIONS, ROUTES
from .schemas import detect_injection_text

SOURCE_RULE = "rule"
SOURCE_MODEL = "model"
STATUS_CANDIDATE = "candidate"


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
    result["route_hypotheses"] = []
    result["conflicts"] = []

    if model_payload is None:
        return result

    if model_payload.get("schema_version") != "0.2":
        enrichment["status"] = "schema_error"
        enrichment["warnings"].append("Model response schema version mismatch")
        return result

    if _check_injection_recursive(model_payload):
        enrichment["status"] = "prompt_injection_warning"
        enrichment["warnings"].append("Prompt injection detected; enrichment skipped")
        return result

    enrichment["applied"] = True
    enrichment["status"] = "ok"

    try:
        _merge_real_goal(result, model_payload)
        _merge_frictions(result, model_payload, enrichment)
        _merge_route_hypotheses(result, model_payload, enrichment)
        _merge_query_terms(result, model_payload)
        _merge_terms(result, model_payload)
        _merge_dialect(result, model_payload)
        _merge_model_warnings(result, model_payload)
    except Exception as exc:
        enrichment["applied"] = False
        enrichment["status"] = "merge_error"
        enrichment["warnings"].append(f"Merge failed: {exc}")
        result["route_hypotheses"] = []

    return result


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
            enrichment.setdefault("warnings", []).append(f"Unknown friction type: {ftype}")
            continue
        if ftype in existing_types:
            continue
        result.setdefault("frictions", []).append({
            "friction_type": ftype,
            "score": min(1.0, max(0.0, float(mf.get("confidence", 0.3)))),
            "matched_signals": mf.get("evidence", []),
            "explanation": mf.get("uncertainty", "Model hypothesis"),
            "source": SOURCE_MODEL, "status": STATUS_CANDIDATE,
        })
    result.setdefault("evidence_trail", []).append({"source": SOURCE_MODEL, "item": "friction_hypotheses"})


def _merge_route_hypotheses(result: dict, model: dict, enrichment: dict) -> None:
    """Model tasks go to route_hypotheses only — never into formal routes."""
    model_tasks = model.get("task_hypotheses", [])
    if not isinstance(model_tasks, list):
        return

    # Build rule task index for matching
    rule_tasks = {r["task"]: r["primary_route"] for r in result.get("routes", [])}
    hypotheses: list[dict] = []

    for mt in model_tasks:
        title = (mt.get("title") or "").strip()
        if not title:
            continue
        routes = [r for r in (mt.get("suggested_routes") or []) if r in ROUTES]
        conflicts: list[str] = []

        # Check per-task SELF/OFFICIAL conflict
        matched_rule_task = title if title in rule_tasks else None
        if matched_rule_task:
            required = rule_tasks[matched_rule_task]
            if required in ("SELF", "OFFICIAL") and routes and routes[0] != required:
                conflicts.append(f"Model suggested {routes[0]} but rules require {required}")

        hypotheses.append({
            "task": title,
            "suggested_routes": routes,
            "expected_deliverable": mt.get("expected_deliverable", ""),
            "requires_user_action": mt.get("requires_user_action", False),
            "sensitivity": mt.get("sensitivity", "low"),
            "source": SOURCE_MODEL,
            "status": STATUS_CANDIDATE,
            "confidence": min(1.0, max(0.0, float(mt.get("confidence", 0.5)))),
            "matched_rule_task": matched_rule_task,
            "conflicts": conflicts,
        })
        if conflicts:
            enrichment.setdefault("warnings", []).extend(
                [f"Route conflict for '{title[:60]}': {c}" for c in conflicts])
            result.setdefault("conflicts", []).extend(conflicts)

    result["route_hypotheses"] = hypotheses
    result.setdefault("evidence_trail", []).append({"source": SOURCE_MODEL, "item": "task_hypotheses"})


def _merge_query_terms(result: dict, model: dict) -> None:
    terms = model.get("query_terms", [])
    if isinstance(terms, list) and terms:
        existing = set(result.get("query_lattice", {}).get("combined_queries", []))
        new = [t for t in terms if isinstance(t, str) and t.strip() not in existing][:8]
        if new:
            result.setdefault("query_lattice", {})["query_terms_model"] = new
            result.setdefault("evidence_trail", []).append(
                {"source": SOURCE_MODEL, "item": "query_terms", "status": STATUS_CANDIDATE})


def _merge_terms(result: dict, model: dict) -> None:
    for field in ("profession_terms", "service_terms"):
        model_terms = model.get(field, [])
        if isinstance(model_terms, list) and model_terms:
            existing = set(result.get("query_lattice", {}).get(field, []))
            new = [t for t in model_terms if isinstance(t, str) and t.strip() not in existing][:8]
            if new:
                result.setdefault("query_lattice", {})[f"{field}_model"] = new
                result.setdefault("evidence_trail", []).append(
                    {"source": SOURCE_MODEL, "item": field, "status": STATUS_CANDIDATE})


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
                "term": term, "canonical_concept": "unknown",
                "possible_services": d.get("possible_meanings", []),
                "expression_type": "candidate", "risk_level": "unknown",
                "confidence": min(1.0, max(0.0, float(d.get("confidence", 0.3)))),
                "evidence_required": d.get("evidence_required", []),
                "source": SOURCE_MODEL, "status": STATUS_CANDIDATE,
            })
    if new:
        result.setdefault("dialect_matches", []).extend(new)
        result.setdefault("evidence_trail", []).append(
            {"source": SOURCE_MODEL, "item": "unknown_dialect_hypotheses", "status": STATUS_CANDIDATE})


def _merge_model_warnings(result: dict, model: dict) -> None:
    warnings = model.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        result.setdefault("model_enrichment", {}).setdefault("warnings", []).extend(
            [w for w in warnings if isinstance(w, str)])


def _check_injection_recursive(obj: Any, _seen: set | None = None) -> bool:
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

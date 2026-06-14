"""Deterministic hybrid merge — rule engine output + model hypotheses.

Governed by these merge rules:
1. Rule risk flags always remain; model cannot lower a rule risk severity.
2. SELF and OFFICIAL routes required by rule stay.
3. Model routes added only as secondary unless a deterministic rule promotes them.
4. Model-generated terms marked `source=model`, `status=candidate`.
5. Unknown dialect meanings never auto-enter verified seed.
6. Conflicts are recorded, safer rule wins.
"""

from __future__ import annotations

from typing import Any

from ..models import (AnalysisResult, FRICTIONS, ROUTES)
from .schemas import detect_injection_text

# ── provenance markers ──────────────────────────────────────────────────────

SOURCE_RULE = "rule"
SOURCE_MODEL = "model"
SOURCE_USER = "user"
SOURCE_SEED = "seed"

STATUS_VERIFIED = "verified"
STATUS_CANDIDATE = "candidate"
STATUS_REJECTED = "rejected"


class MergeMeta:
    """Provenance wrapper for a merged item."""

    __slots__ = ("value", "source", "confidence", "matched_evidence",
                 "status", "conflicts")

    def __init__(self, *, value: Any, source: str, confidence: float = 0.0,
                 matched_evidence: list[str] | None = None,
                 status: str = STATUS_CANDIDATE, conflicts: list[str] | None = None):
        self.value = value
        self.source = source
        self.confidence = confidence
        self.matched_evidence = matched_evidence or []
        self.status = status
        self.conflicts = conflicts or []


def merge_analysis(
    rule_result: AnalysisResult,
    model_payload: dict[str, Any] | None,
    model_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Merge rule engine output with model hypotheses. Returns an enriched dict.

    Args:
        rule_result: The deterministic engine output (always present).
        model_payload: Parsed model JSON, or None if model failed.
        model_warnings: Warnings accumulated during model call attempt.
    """
    enrichment = {
        "attempted": True,
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

    # ── schema version guard ──
    if model_payload.get("schema_version") != "0.2":
        enrichment["status"] = "schema_error"
        enrichment["warnings"].append("Model response schema version mismatch")
        return result

    # ── injection check ──
    injection_detected = False
    real_goal = model_payload.get("real_goal", "")
    if isinstance(real_goal, str) and detect_injection_text(real_goal):
        enrichment["warnings"].append("Prompt injection detected in model output")
        injection_detected = True

    enrichment["applied"] = True
    enrichment["status"] = "ok"

    # ── merge rule friction with model friction ──
    _merge_frictions(result, model_payload, enrichment)

    # ── merge routes — preserve SELF/OFFICIAL ──
    _merge_routes(result, model_payload, enrichment)

    # ── merge model terms (candidate status only) ──
    _merge_terms(result, model_payload)

    # ── merge dialect hypotheses ──
    _merge_dialect(result, model_payload)

    if injection_detected:
        enrichment["status"] = "prompt_injection_warning"

    return result


def _merge_frictions(result: dict, model: dict, enrichment: dict) -> None:
    model_frictions = model.get("friction_hypotheses", [])
    if not isinstance(model_frictions, list):
        return
    existing_types = {f["friction_type"] for f in result.get("frictions", [])}
    for mf in model_frictions:
        ftype = mf.get("type")
        if ftype not in FRICTIONS:
            enrichment.setdefault("warnings", []).append(
                f"Model returned unknown friction type: {ftype}"
            )
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
    evidence = {"source": SOURCE_MODEL, "item": "friction_hypotheses"}
    result.setdefault("evidence_trail", []).append(evidence)


def _merge_routes(result: dict, model: dict, enrichment: dict) -> None:
    existing_tasks = {r["task"] for r in result.get("routes", [])}
    required_routes = {
        r["primary_route"]
        for r in result.get("routes", [])
        if r.get("primary_route") in ("SELF", "OFFICIAL")
        or any(s in ("SELF", "OFFICIAL") for s in r.get("secondary_routes", []))
    }

    model_tasks = model.get("task_hypotheses", [])
    if not isinstance(model_tasks, list):
        return

    for mt in model_tasks:
        title = (mt.get("title") or "").strip()
        if not title or title in existing_tasks:
            continue
        routes = [r for r in (mt.get("suggested_routes") or []) if r in ROUTES]
        if not routes:
            continue

        conflicts = []
        primary = routes[0]
        secondaries = routes[1:] if len(routes) > 1 else []

        if "SELF" in required_routes and primary == "MARKET":
            conflicts.append(
                "Model suggested MARKET where SELF is required; keeping SELF"
            )
            enrichment.setdefault("warnings", []).append(conflicts[-1])
            secondaries = [primary] + [s for s in secondaries if s != "SELF"]
            primary = "SELF"

        if "OFFICIAL" in required_routes and primary in ("MARKET", "AI"):
            conflicts.append(
                "Model suggested non-OFFICIAL where OFFICIAL is required; keeping OFFICIAL"
            )
            enrichment.setdefault("warnings", []).append(conflicts[-1])
            secondaries = [primary] + [s for s in secondaries if s != "OFFICIAL"]
            primary = "OFFICIAL"

        result.setdefault("routes", []).append({
            "task": title,
            "primary_route": primary,
            "secondary_routes": secondaries,
            "market_stage": "candidate",
            "confidence": min(1.0, max(0.0, 0.5)),
            "reasons": ["Model hypothesis — requires validation"],
            "human_gate": mt.get("sensitivity") == "high",
            "source": SOURCE_MODEL,
            "status": STATUS_CANDIDATE,
        })
        if conflicts:
            result.setdefault("conflicts", []).extend(conflicts)

    evidence = {"source": SOURCE_MODEL, "item": "task_hypotheses"}
    result.setdefault("evidence_trail", []).append(evidence)


def _merge_terms(result: dict, model: dict) -> None:
    """Add model-generated profession/service/query terms as candidates."""
    for field, key in [("profession_terms", "profession_terms"),
                       ("service_terms", "service_terms")]:
        model_terms = model.get(key, [])
        if isinstance(model_terms, list) and model_terms:
            existing = set(result.get("query_lattice", {}).get(field, []))
            new = [
                t for t in model_terms
                if isinstance(t, str) and t.strip() not in existing
            ][:8]
            if new:
                result.setdefault("query_lattice", {})[
                    f"{field}_model"
                ] = new
                evidence = {
                    "source": SOURCE_MODEL, "item": key,
                    "status": STATUS_CANDIDATE,
                }
                result.setdefault("evidence_trail", []).append(evidence)


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
        evidence = {
            "source": SOURCE_MODEL, "item": "unknown_dialect_hypotheses",
            "status": STATUS_CANDIDATE,
        }
        result.setdefault("evidence_trail", []).append(evidence)

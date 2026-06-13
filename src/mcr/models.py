from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

ROUTES = {"AI", "TOOL", "SELF", "PROFESSIONAL", "MARKET", "OFFICIAL"}
FRICTIONS = {"knowledge", "diagnosis", "skill", "channel", "execution", "verification"}


@dataclass
class FrictionResult:
    friction_type: str
    score: float
    matched_signals: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class RouteDecision:
    task: str
    primary_route: str
    secondary_routes: list[str] = field(default_factory=list)
    market_stage: str = "none"
    confidence: float = 0.5
    reasons: list[str] = field(default_factory=list)
    human_gate: bool = False


@dataclass
class RiskFlag:
    rule_id: str
    category: str
    severity: str
    matched_evidence: str
    explanation: str
    recommended_action: str
    human_confirmation_required: bool = False


@dataclass
class CandidateEvaluation:
    relevance: int
    professionalism: int
    deliverable_clarity: int
    trust: int
    verifiability: int
    risk: int
    status: str
    reasons: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    risk_flags: list[RiskFlag] = field(default_factory=list)


@dataclass
class AnalysisResult:
    goal: str
    frictions: list[FrictionResult]
    routes: list[RouteDecision]
    market_recommended: bool
    recommended_service_level: str
    query_lattice: dict[str, list[str]]
    dialect_matches: list[dict[str, Any]]
    risk_flags: list[RiskFlag]
    human_gates: list[str]
    execution_order: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

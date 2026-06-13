from __future__ import annotations

from .data import DataRepository
from .models import RiskFlag

SEVERITY_SCORE = {"low": 10, "medium": 30, "high": 60, "critical": 100}


class RiskEngine:
    def __init__(self, repo: DataRepository | None = None):
        self.repo = repo or DataRepository()
        self.rules = self.repo.load("risk_rules.json")

    def scan(self, text: str) -> list[RiskFlag]:
        lower = text.lower()
        flags: list[RiskFlag] = []
        for rule in self.rules:
            match = next((signal for signal in rule["signals"] if signal.lower() in lower), None)
            if match:
                flags.append(RiskFlag(
                    rule_id=rule["id"],
                    category=rule["category"],
                    severity=rule["severity"],
                    matched_evidence=match,
                    explanation=rule["explanation"],
                    recommended_action=rule["recommended_action"],
                    human_confirmation_required=rule.get("human_confirmation_required", False),
                ))
        return flags

    @staticmethod
    def score(flags: list[RiskFlag]) -> int:
        if any(flag.severity == "critical" for flag in flags):
            return 100
        total = sum(SEVERITY_SCORE.get(flag.severity, 20) for flag in flags)
        return min(100, total)

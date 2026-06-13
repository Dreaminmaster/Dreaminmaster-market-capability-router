from __future__ import annotations

from datetime import date, datetime

from .data import DataRepository


class PlatformDialectEngine:
    def __init__(self, repo: DataRepository | None = None):
        self.repo = repo or DataRepository()
        self.terms = self.repo.load("platform_terms.json")

    @staticmethod
    def _age_days(date_text: str) -> int:
        try:
            return (date.today() - datetime.strptime(date_text, "%Y-%m-%d").date()).days
        except Exception:
            return 9999

    def interpret(self, text: str) -> list[dict]:
        matches = []
        lower = text.lower()
        for entry in self.terms:
            term = entry["term"]
            if term.lower() in lower:
                confidence = float(entry.get("confidence", 0.5))
                age = self._age_days(entry.get("last_verified", ""))
                if age > 180:
                    confidence *= 0.75
                matches.append({
                    "term": term,
                    "canonical_concept": entry["canonical_concept"],
                    "possible_services": entry.get("possible_services", []),
                    "expression_type": entry.get("expression_type", "unknown"),
                    "risk_level": entry.get("risk_level", "unknown"),
                    "confidence": round(confidence, 2),
                    "evidence_required": entry.get("evidence_required", []),
                    "last_verified": entry.get("last_verified"),
                    "status": entry.get("status", "candidate"),
                })
        return sorted(matches, key=lambda item: item["confidence"], reverse=True)

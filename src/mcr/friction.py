from __future__ import annotations

from .data import DataRepository
from .models import FrictionResult


class FrictionDiagnoser:
    def __init__(self, repo: DataRepository | None = None):
        self.repo = repo or DataRepository()
        self.rules = self.repo.load("friction_types.json")

    def diagnose(self, text: str) -> list[FrictionResult]:
        normalized = text.lower()
        results: list[FrictionResult] = []
        for item in self.rules:
            matches = [signal for signal in item["signals"] if signal.lower() in normalized]
            base = item.get("base_score", 0.1)
            score = min(1.0, base + len(matches) * item.get("signal_weight", 0.18))
            if matches or score >= item.get("emit_threshold", 0.3):
                results.append(
                    FrictionResult(
                        friction_type=item["id"],
                        score=round(score, 2),
                        matched_signals=matches,
                        explanation=item["description"],
                    )
                )
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:3]

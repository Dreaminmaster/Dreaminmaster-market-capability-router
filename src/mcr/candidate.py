from __future__ import annotations

from typing import Any

from .models import CandidateEvaluation
from .risk import RiskEngine


class CandidateEvaluator:
    def __init__(self, risk_engine: RiskEngine | None = None):
        self.risk_engine = risk_engine or RiskEngine()

    @staticmethod
    def _text(candidate: dict[str, Any]) -> str:
        parts = [
            str(candidate.get("title", "")),
            str(candidate.get("description", "")),
            " ".join(candidate.get("deliverables", [])),
            " ".join(candidate.get("required_data", [])),
            " ".join(candidate.get("claims", [])),
        ]
        return " ".join(parts)

    def evaluate(self, candidate: dict[str, Any], need_terms: list[str] | None = None) -> CandidateEvaluation:
        text = self._text(candidate)
        need_terms = need_terms or []
        flags = self.risk_engine.scan(text)
        risk = self.risk_engine.score(flags)

        relevance_hits = sum(1 for term in need_terms if term and term in text)
        relevance = min(100, 35 + relevance_hits * 20) if need_terms else 55

        deliverables = candidate.get("deliverables", [])
        price_model = candidate.get("price_model")
        background = candidate.get("provider_background")
        evidence = candidate.get("evidence", [])

        clarity = 30 + min(50, len(deliverables) * 15) + (15 if price_model else 0)
        professionalism = 45 + (25 if background else 0) + (10 if candidate.get("limitations") else 0)
        trust = 40 + min(30, len(evidence) * 10)
        verifiability = 35 + min(45, len(deliverables) * 10) + (10 if candidate.get("trial_available") else 0)

        if any(word in text for word in ["具体私聊", "拍前联系", "不是实物"]):
            clarity -= 15
        if not deliverables:
            clarity -= 20
        if not price_model:
            trust -= 10

        relevance = max(0, min(100, relevance))
        clarity = max(0, min(100, clarity))
        professionalism = max(0, min(100, professionalism))
        trust = max(0, min(100, trust))
        verifiability = max(0, min(100, verifiability))

        if risk >= 80:
            status = "blocked"
        elif risk >= 50 or clarity < 45:
            status = "needs_verification"
        elif relevance >= 60 and clarity >= 55:
            status = "worth_asking"
        else:
            status = "low_match"

        reasons = []
        if deliverables:
            reasons.append("交付物已列明")
        else:
            reasons.append("未明确交付物")
        if price_model:
            reasons.append("价格结构有说明")
        else:
            reasons.append("价格可能是占位价或尚未说明")
        if background:
            reasons.append("提供者声明了相关背景，仍需验证")
        if flags:
            reasons.extend([f"风险：{f.explanation}" for f in flags])

        questions = [
            "你提供的是诊断、审核、指导还是代操作？",
            "最终会交付什么文件、标注或结论？",
            "当前价格是总价、定金还是咨询费？",
            "是否需要账号密码、验证码、身份证件或远程控制？",
            "无法完成时如何收费，是否可以先进行低价初步诊断？",
        ]

        return CandidateEvaluation(
            relevance=relevance,
            professionalism=professionalism,
            deliverable_clarity=clarity,
            trust=trust,
            verifiability=verifiability,
            risk=risk,
            status=status,
            reasons=reasons,
            questions=questions,
            risk_flags=flags,
        )

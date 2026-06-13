from __future__ import annotations

from .data import DataRepository
from .models import FrictionResult


class QueryLatticeGenerator:
    def __init__(self, repo: DataRepository | None = None):
        self.repo = repo or DataRepository()
        self.professions = self.repo.load("professions.json")
        self.service_standards = self.repo.load("service_delivery_standards.json")

    @staticmethod
    def _unique(items: list[str], limit: int = 12) -> list[str]:
        seen = set()
        out = []
        for item in items:
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                out.append(item)
            if len(out) >= limit:
                break
        return out

    def generate(self, text: str, frictions: list[FrictionResult]) -> dict[str, list[str]]:
        problem_terms = []
        action_terms = []
        deliverable_terms = []
        profession_terms = []
        platform_terms = ["咨询", "看单", "把关", "排雷", "过一遍"]
        risk_filters = ["包过", "百分百", "内部渠道", "先平台外付款", "索要验证码"]

        domain_hits = []
        for standard in self.service_standards:
            if any(k in text for k in standard["trigger_terms"]):
                domain_hits.append(standard)
                problem_terms.extend(standard["problem_terms"])
                action_terms.extend(standard["action_terms"])
                deliverable_terms.extend(standard["deliverables"])

        for profession in self.professions:
            if any(k in text for k in profession["trigger_terms"]):
                profession_terms.extend(profession["roles"])

        friction_ids = {f.friction_type for f in frictions}
        if "diagnosis" in friction_ids:
            action_terms.extend(["诊断", "原因分析", "问题定位"])
        if "verification" in friction_ids:
            action_terms.extend(["审核", "复核", "第二意见"])
        if "skill" in friction_ids:
            action_terms.extend(["指导", "陪跑", "远程协助"])
        if "channel" in friction_ids:
            action_terms.extend(["渠道比较", "方案比价", "合法优惠"])
        if "execution" in friction_ids:
            action_terms.extend(["代办事项拆分", "现场协助", "部分执行"])

        if not problem_terms:
            short = text.strip().replace("，", " ").replace("。", " ")[:30]
            problem_terms.append(short)
        if not profession_terms:
            profession_terms.extend(["相关行业从业者", "独立顾问", "有同类经验的过来人"])
        if not deliverable_terms:
            deliverable_terms.extend(["诊断结论", "风险清单", "修改建议", "执行步骤"])

        combined = []
        for p in self._unique(problem_terms, 4):
            for a in self._unique(action_terms, 4):
                combined.append(f"{p} {a}")
        for role in self._unique(profession_terms, 4):
            for a in self._unique(action_terms, 3):
                combined.append(f"{role} {a}")

        return {
            "problem_terms": self._unique(problem_terms),
            "action_terms": self._unique(action_terms),
            "deliverable_terms": self._unique(deliverable_terms),
            "profession_terms": self._unique(profession_terms),
            "platform_expressions": self._unique(platform_terms),
            "risk_filters": self._unique(risk_filters),
            "combined_queries": self._unique(combined, 16),
        }

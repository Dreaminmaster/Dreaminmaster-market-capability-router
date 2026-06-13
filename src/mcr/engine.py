from __future__ import annotations

from .dialect import PlatformDialectEngine
from .friction import FrictionDiagnoser
from .models import AnalysisResult
from .query_lattice import QueryLatticeGenerator
from .risk import RiskEngine
from .router import CapabilityRouter


class MarketCapabilityRouter:
    def __init__(self):
        self.friction = FrictionDiagnoser()
        self.router = CapabilityRouter()
        self.query = QueryLatticeGenerator()
        self.dialect = PlatformDialectEngine()
        self.risk = RiskEngine()

    def analyze(self, text: str) -> AnalysisResult:
        frictions = self.friction.diagnose(text)
        routes = self.router.route(text, frictions)
        query_lattice = self.query.generate(text, frictions)
        dialect_matches = self.dialect.interpret(text)
        risk_flags = self.risk.scan(text)

        market_routes = [r for r in routes if r.primary_route == "MARKET" or "MARKET" in r.secondary_routes]
        market_recommended = bool(market_routes) and not any(f.severity == "critical" for f in risk_flags)
        stages = [r.market_stage for r in market_routes if r.market_stage != "none"]
        recommended_service_level = stages[0] if stages else "information"

        human_gates = []
        if any(r.human_gate for r in routes):
            human_gates.append("在提供敏感资料、付款、签字、登录或正式提交前由用户本人确认")
        if risk_flags:
            human_gates.append("先核实风险信号，不因相关度高而跳过验证")

        execution_order = [
            "先确认官方规则和可公开验证的信息",
            "使用 AI 与工具完成低成本初筛",
        ]
        if market_recommended:
            execution_order.extend([
                f"优先购买 {recommended_service_level} 层级的最小必要服务",
                "使用查询网格寻找候选并统一比较交付物、价格和权限要求",
                "在交易前完成风险追问和人工确认",
            ])
        execution_order.append("完成后记录脱敏结果，用于改进词条和路由")

        return AnalysisResult(
            goal=text.strip(),
            frictions=frictions,
            routes=routes,
            market_recommended=market_recommended,
            recommended_service_level=recommended_service_level,
            query_lattice=query_lattice,
            dialect_matches=dialect_matches,
            risk_flags=risk_flags,
            human_gates=human_gates,
            execution_order=execution_order,
        )

from __future__ import annotations

from typing import Any

from .adapters.llm.base import (
    LLMAdapter, LLMResponse,
    STATUS_NOT_CONFIGURED, STATUS_OK, STATUS_TIMEOUT,
    STATUS_CONNECTION_ERROR, STATUS_AUTH_ERROR, STATUS_HTTP_ERROR,
    STATUS_INVALID_JSON, STATUS_SCHEMA_ERROR, STATUS_RESPONSE_TOO_LARGE,
    STATUS_PROMPT_INJECTION,
)
from .dialect import PlatformDialectEngine
from .friction import FrictionDiagnoser
from .models import AnalysisResult
from .query_lattice import QueryLatticeGenerator
from .risk import RiskEngine
from .router import CapabilityRouter
from .hybrid.merge import merge_analysis
from .hybrid.config import LLMConfig
from .simple_guard import should_use_capability_router


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

        market_routes = [
            r for r in routes
            if r.primary_route == "MARKET" or "MARKET" in r.secondary_routes
        ]
        market_recommended = bool(market_routes) and not any(
            f.severity == "critical" for f in risk_flags
        )
        stages = [r.market_stage for r in market_routes if r.market_stage != "none"]
        recommended_service_level = stages[0] if stages else "information"

        human_gates: list[str] = []
        if any(r.human_gate for r in routes):
            human_gates.append("在提供敏感资料、付款、签字、登录或正式提交前由用户本人确认")
        if risk_flags:
            human_gates.append("先核实风险信号，不因相关度高而跳过验证")

        execution_order: list[str] = [
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

    def analyze_with_model(
        self, text: str, *, adapter: LLMAdapter | None, config: LLMConfig | None = None,
    ) -> dict[str, Any]:
        rule_result = self.analyze(text)
        warnings: list[str] = []

        # Simple task gate
        if not should_use_capability_router(text):
            return merge_analysis(rule_result, None, warnings)

        # Not configured
        if adapter is None or config is None or not config.configured:
            result = merge_analysis(rule_result, None, warnings)
            result["model_enrichment"]["attempted"] = False
            result["model_enrichment"]["status"] = STATUS_NOT_CONFIGURED
            return result

        # Redact
        from .hybrid.validation import redact_recursive
        redacted_text, redact_warnings = redact_recursive(text)
        warnings.extend(redact_warnings)

        from .hybrid.prompts import SYSTEM_PROMPT, build_user_payload
        from .hybrid.schemas import ANALYSIS_SCHEMA, validate_schema

        user_payload = build_user_payload(
            request_text=redacted_text,
            rule_frictions=[
                {"type": f.friction_type, "confidence": f.score, "evidence": f.matched_signals}
                for f in rule_result.frictions
            ],
            rule_routes=[
                {"title": r.task, "route": r.primary_route}
                for r in rule_result.routes
            ],
        )

        model_payload: dict[str, Any] | None = None
        model_status = STATUS_NOT_CONFIGURED
        attempted = False

        attempted = True
        response: LLMResponse = adapter.complete_json(
            system=SYSTEM_PROMPT, user_payload=user_payload,
            schema=ANALYSIS_SCHEMA, timeout_seconds=config.timeout_seconds,
        )
        warnings.extend(response.warnings)
        model_status = response.status

        if response.status == STATUS_OK and response.parsed:
            model_payload = response.parsed
            from mcr.hybrid.merge import _check_injection_recursive
            if _check_injection_recursive(model_payload):
                warnings.append("Prompt injection detected in model output")
                model_payload = None
                model_status = STATUS_PROMPT_INJECTION
            else:
                schema_errors = validate_schema(model_payload)
                if schema_errors:
                    warnings.append("Schema validation failed")
                    warnings.extend(schema_errors)
                    model_payload = None
                    model_status = STATUS_SCHEMA_ERROR
        elif response.status == STATUS_OK and not response.parsed:
            model_status = STATUS_INVALID_JSON

        merged = merge_analysis(rule_result, model_payload, warnings)
        merged["model_enrichment"]["attempted"] = attempted
        merged["model_enrichment"]["status"] = model_status
        return merged

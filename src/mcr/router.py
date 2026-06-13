from __future__ import annotations

from .models import FrictionResult, RouteDecision

SENSITIVE_TERMS = ["密码", "验证码", "身份证", "银行卡", "支付", "实名", "签字", "远程控制"]
OFFICIAL_TERMS = ["申诉", "签证", "银行争议", "学校申诉", "封号", "解封", "退款", "身份修改"]
PROFESSIONAL_TERMS = ["法律", "医疗", "诊断", "验房", "电工", "结构", "审计", "税务", "合同"]
EXECUTION_TERMS = ["跑腿", "现场", "拍照", "看房", "搬家", "代取", "异地"]


class CapabilityRouter:
    def route(self, text: str, frictions: list[FrictionResult]) -> list[RouteDecision]:
        routes: list[RouteDecision] = []
        lower = text.lower()
        sensitive = any(term in lower for term in SENSITIVE_TERMS)

        routes.append(RouteDecision(
            task="理解问题、整理已有信息并形成初步方案",
            primary_route="AI",
            secondary_routes=["TOOL"],
            market_stage="information",
            confidence=0.92,
            reasons=["信息整理和初步分析可低成本完成"],
            human_gate=False,
        ))

        if any(term in lower for term in OFFICIAL_TERMS):
            routes.append(RouteDecision(
                task="确认规则并完成正式提交或决定",
                primary_route="OFFICIAL",
                secondary_routes=["SELF"],
                market_stage="review",
                confidence=0.95,
                reasons=["最终决定权属于官方渠道", "外部服务最多提供诊断或材料审核"],
                human_gate=True,
            ))

        friction_ids = {f.friction_type for f in frictions}
        if "verification" in friction_ids or "skill" in friction_ids:
            routes.append(RouteDecision(
                task="获取独立审核、第二意见或专业复核",
                primary_route="MARKET",
                secondary_routes=["PROFESSIONAL"],
                market_stage="review",
                confidence=0.82,
                reasons=["独立复核可减少高成本错误", "优先购买审核而不是完整代办"],
                human_gate=sensitive,
            ))
        elif "diagnosis" in friction_ids:
            routes.append(RouteDecision(
                task="定位失败原因并判断下一步",
                primary_route="MARKET",
                secondary_routes=["AI", "PROFESSIONAL"],
                market_stage="diagnosis",
                confidence=0.78,
                reasons=["先购买诊断比直接代办更可验证"],
                human_gate=sensitive,
            ))
        elif "channel" in friction_ids:
            routes.append(RouteDecision(
                task="比较合法渠道和服务方案",
                primary_route="TOOL",
                secondary_routes=["MARKET", "OFFICIAL"],
                market_stage="information",
                confidence=0.76,
                reasons=["先公开比较渠道，避免将所谓内部关系作为默认方案"],
                human_gate=sensitive,
            ))

        if any(term in lower for term in PROFESSIONAL_TERMS):
            routes.append(RouteDecision(
                task="处理需要资质或高责任判断的部分",
                primary_route="PROFESSIONAL",
                secondary_routes=["OFFICIAL"],
                market_stage="professional_service",
                confidence=0.9,
                reasons=["失败成本和专业门槛较高"],
                human_gate=True,
            ))

        if any(term in lower for term in EXECUTION_TERMS):
            routes.append(RouteDecision(
                task="完成现实现场或异地执行",
                primary_route="MARKET",
                secondary_routes=["SELF"],
                market_stage="partial_execution",
                confidence=0.8,
                reasons=["任务需要现实世界执行能力"],
                human_gate=True,
            ))

        if sensitive:
            routes.append(RouteDecision(
                task="提供敏感资料、登录、付款、签字或最终确认",
                primary_route="SELF",
                secondary_routes=["OFFICIAL"],
                market_stage="none",
                confidence=0.98,
                reasons=["敏感权限和最终责任不能默认交给陌生服务者"],
                human_gate=True,
            ))

        seen = set()
        output = []
        for route in routes:
            if route.task not in seen:
                seen.add(route.task)
                output.append(route)
        return output

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcr.candidate import CandidateEvaluator
from mcr.engine import MarketCapabilityRouter


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify OpenMinis prerequisites for MCR")
    parser.add_argument("--skill-root", default="/var/minis/skills")
    args = parser.parse_args()

    skill = Path(args.skill_root).expanduser() / "market-capability-router" / "SKILL.md"
    checks: list[tuple[str, bool]] = []
    checks.append((f"skill file: {skill}", skill.exists()))

    analysis = MarketCapabilityRouter().analyze("装修报价单看不懂，担心增项，想找人审核")
    checks.append(("analysis recommends market review", analysis.market_recommended and analysis.recommended_service_level == "review"))

    risky = {
        "title": "账号秒解 百分百成功 内部渠道",
        "description": "需要账号密码和验证码，微信转账后远程登录处理。",
        "deliverables": [],
        "price_model": "实际价格私聊",
    }
    evaluation = CandidateEvaluator().evaluate(risky, ["账号", "解封"])
    checks.append(("critical candidate is blocked", evaluation.status == "blocked" and evaluation.risk == 100))

    for label, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'} {label}")
    print(json.dumps({"passed": sum(ok for _, ok in checks), "total": len(checks)}, ensure_ascii=False))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

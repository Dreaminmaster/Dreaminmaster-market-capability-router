#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from mcr.engine import MarketCapabilityRouter


def evaluate_case(engine, case):
    result = engine.analyze(case["input"])
    expect = case["expect"]
    checks = []
    if "friction" in expect:
        checks.append(expect["friction"] in {f.friction_type for f in result.frictions})
    if "route" in expect:
        checks.append(expect["route"] in {r.primary_route for r in result.routes})
    if "market" in expect:
        checks.append(result.market_recommended is expect["market"])
    if "query_contains" in expect:
        all_terms = sum(result.query_lattice.values(), [])
        checks.append(any(expect["query_contains"] in x for x in all_terms))
    if "critical_risk" in expect:
        checks.append(any(f.severity == "critical" for f in result.risk_flags) is expect["critical_risk"])
    if "high_risk" in expect:
        checks.append(any(f.severity in {"high", "critical"} for f in result.risk_flags) is expect["high_risk"])
    if "dialect" in expect:
        checks.append(expect["dialect"] in {m["canonical_concept"] for m in result.dialect_matches})
    return all(checks), checks


def main() -> int:
    cases = json.loads(Path("evals/cases/core_cases.json").read_text(encoding="utf-8"))
    engine = MarketCapabilityRouter()
    passed = 0
    for case in cases:
        ok, checks = evaluate_case(engine, case)
        passed += int(ok)
        print(f"{'PASS' if ok else 'FAIL'} {case['id']} {checks}")
    rate = passed / len(cases)
    print(f"Result: {passed}/{len(cases)} = {rate:.0%}")
    return 0 if rate >= 0.9 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run product evaluation cases against the current engine.

Supports:
- "friction": string → exact match; list → any-of match
- "route": string → match any primary route
- "market": true/false
- "query_contains": substring in any query lattice term
- "critical_risk": true/false
- "high_risk": true/false
- "dialect": canonical_concept match
- "no_risk": true → no critical or high risk flags
- "any_friction": true → at least one friction detected
- "at_least_one_route_contains": substring in any route task
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcr.engine import MarketCapabilityRouter


def evaluate_case(engine: MarketCapabilityRouter, case: dict[str, Any]) -> tuple[bool, list[bool]]:
    result = engine.analyze(case["input"])
    expect = case["expect"]
    checks: list[bool] = []

    if "friction" in expect:
        want = expect["friction"]
        friction_types = {f.friction_type for f in result.frictions}
        if isinstance(want, list):
            checks.append(bool(friction_types & set(want)))
        else:
            checks.append(want in friction_types)

    if "any_friction" in expect:
        checks.append(len(result.frictions) > 0)

    if "route" in expect:
        want = expect["route"]
        route_set = {r.primary_route for r in result.routes}
        if isinstance(want, list):
            checks.append(bool(route_set & set(want)))
        else:
            checks.append(want in route_set)

    if "at_least_one_route_contains" in expect:
        want = expect["at_least_one_route_contains"]
        checks.append(any(want.lower() in r.task.lower() for r in result.routes))

    if "market" in expect:
        checks.append(result.market_recommended is expect["market"])

    if "query_contains" in expect:
        all_terms: list[str] = []
        for key, value in result.query_lattice.items():
            if isinstance(value, list):
                all_terms.extend([str(x) for x in value])
        checks.append(any(expect["query_contains"] in x for x in all_terms))

    if "critical_risk" in expect:
        has_critical = any(f.severity == "critical" for f in result.risk_flags)
        checks.append(has_critical is expect["critical_risk"])

    if "high_risk" in expect:
        has_high = any(f.severity in {"high", "critical"} for f in result.risk_flags)
        checks.append(has_high is expect["high_risk"])

    if "no_risk" in expect:
        has_any = any(f.severity in {"high", "critical"} for f in result.risk_flags)
        checks.append(has_any is False)

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

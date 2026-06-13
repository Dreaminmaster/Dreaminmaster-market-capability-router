#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REQUIRED = {
    "friction_types.json": {"id", "description", "signals"},
    "professions.json": {"domain", "trigger_terms", "roles"},
    "platform_terms.json": {"term", "canonical_concept", "platform", "expression_type", "risk_level", "confidence", "last_verified", "status"},
    "risk_rules.json": {"id", "category", "severity", "signals", "explanation", "recommended_action"},
    "service_delivery_standards.json": {"id", "trigger_terms", "problem_terms", "action_terms", "deliverables"},
}


def main() -> int:
    base = Path("data/seed")
    errors = []
    for name, fields in REQUIRED.items():
        path = base / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{name}: cannot read: {exc}")
            continue
        if not isinstance(data, list) or not data:
            errors.append(f"{name}: must be a non-empty list")
            continue
        for i, item in enumerate(data):
            missing = fields - set(item)
            if missing:
                errors.append(f"{name}[{i}]: missing {sorted(missing)}")
            if name == "platform_terms.json":
                try:
                    datetime.strptime(item["last_verified"], "%Y-%m-%d")
                except Exception:
                    errors.append(f"{name}[{i}]: invalid last_verified")
                if not 0 <= item.get("confidence", -1) <= 1:
                    errors.append(f"{name}[{i}]: confidence out of range")
    if errors:
        print("DATA VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DATA VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

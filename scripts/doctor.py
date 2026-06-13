#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import platform
import sys
from pathlib import Path


def main() -> int:
    print("Market Capability Router doctor")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Repository: {Path.cwd()}")
    ok = sys.version_info >= (3, 10)
    print(f"Python >= 3.10: {'PASS' if ok else 'FAIL'}")
    print(f"mcr importable: {'PASS' if importlib.util.find_spec('mcr') else 'FAIL (run pip install -e .)'}")
    for path in ["data/seed", "skills/market-capability-router/SKILL.md", "evals/cases/core_cases.json"]:
        exists = Path(path).exists()
        print(f"{path}: {'PASS' if exists else 'FAIL'}")
        ok = ok and exists
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Market Capability Router skill")
    parser.add_argument("--target", required=True, help="Agent skills directory")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation")
    args = parser.parse_args()

    source = Path("skills/market-capability-router").resolve()
    target_root = Path(args.target).expanduser().resolve()
    target = target_root / source.name
    if not source.exists():
        print(f"Source not found: {source}")
        return 2
    if target.exists():
        if not args.force:
            print(f"Target already exists: {target}. Use --force to replace it.")
            return 2
        shutil.rmtree(target)
    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    print(f"Installed skill to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

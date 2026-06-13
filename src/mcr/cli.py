from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .candidate import CandidateEvaluator
from .engine import MarketCapabilityRouter
from .api import serve


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_analyze(args: argparse.Namespace) -> int:
    engine = MarketCapabilityRouter()
    result = engine.analyze(args.text)
    _print_json(result.to_dict())
    return 0


def cmd_candidate(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Unable to read candidate file: {exc}", file=sys.stderr)
        return 2
    evaluator = CandidateEvaluator()
    result = evaluator.evaluate(candidate, need_terms=args.need)
    _print_json(result.__dict__ | {"risk_flags": [f.__dict__ for f in result.risk_flags]})
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    serve(args.host, args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcr", description="Market Capability Router")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Analyze a real-world problem")
    analyze.add_argument("text")
    analyze.set_defaults(func=cmd_analyze)

    candidate = sub.add_parser("candidate", help="Evaluate a candidate service JSON file")
    candidate.add_argument("file")
    candidate.add_argument("--need", action="append", default=[], help="Required term; repeatable")
    candidate.set_defaults(func=cmd_candidate)

    api = sub.add_parser("serve", help="Run the local HTTP API")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)
    api.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

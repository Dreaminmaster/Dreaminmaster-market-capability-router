from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from .candidate import CandidateEvaluator
from .engine import MarketCapabilityRouter
from .api import serve


def _print_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _load_text(source: str, stdin: TextIO | None = None) -> str:
    stream = stdin or sys.stdin
    try:
        if source == "-":
            text = stream.read()
        elif source.startswith("@"):
            text = Path(source[1:]).read_text(encoding="utf-8")
        else:
            text = source
    except Exception as exc:
        raise ValueError(f"Unable to read input text: {exc}") from exc
    if not text.strip():
        raise ValueError("input text must not be empty")
    return text.strip()


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        text = _load_text(args.text)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    engine = MarketCapabilityRouter()
    result = engine.analyze(text)
    _print_json(result.to_dict())
    return 0


def _load_candidate(source: str, stdin: TextIO | None = None) -> dict:
    stream = stdin or sys.stdin
    try:
        if source == "-":
            raw = stream.read()
        else:
            raw = Path(source).read_text(encoding="utf-8")
        candidate = json.loads(raw)
        if not isinstance(candidate, dict):
            raise ValueError("candidate JSON must be an object")
        return candidate
    except Exception as exc:
        raise ValueError(f"Unable to read candidate JSON: {exc}") from exc


def cmd_candidate(args: argparse.Namespace) -> int:
    try:
        candidate = _load_candidate(args.file)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
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

    analyze = sub.add_parser("analyze", help="Analyze text, - for stdin, or @path for a UTF-8 file")
    analyze.add_argument("text", help="Problem text, - for stdin, or @path")
    analyze.set_defaults(func=cmd_analyze)

    candidate = sub.add_parser("candidate", help="Evaluate candidate JSON from a file or stdin")
    candidate.add_argument("file", help="JSON file path, or - to read JSON from stdin")
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

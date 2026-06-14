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

    mode = getattr(args, "mode", "rules") or "rules"
    if mode == "rules":
        result = engine.analyze(text)
        _print_json(result.to_dict())
        return 0

    if mode == "hybrid":
        from .hybrid.config import resolve_config
        config = resolve_config(
            base_url=getattr(args, "llm_base_url", None),
            api_key=getattr(args, "llm_api_key", None),
            model=getattr(args, "llm_model", None),
            timeout_seconds=getattr(args, "llm_timeout", None),
            max_retries=getattr(args, "llm_max_retries", None),
        )

        adapter = None
        if config.configured:
            from .adapters.llm.openai_compatible import OpenAICompatibleAdapter
            adapter = OpenAICompatibleAdapter(
                base_url=config.base_url,
                model=config.model,
                api_key=config.api_key,
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
            )

        merged = engine.analyze_with_model(text, adapter=adapter, config=config)
        _print_json(merged)
        return 0

    if mode == "model":
        print(
            "ERROR: --mode model is not supported in v0.2. Use --mode rules or --mode hybrid.",
            file=sys.stderr,
        )
        return 2

    print(f"ERROR: unknown mode {mode!r}", file=sys.stderr)
    return 2


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
    _print_json(
        result.__dict__
        | {"risk_flags": [f.__dict__ for f in result.risk_flags]}
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    serve(args.host, args.port)
    return 0


def _add_llm_flags(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--mode", choices=["rules", "hybrid", "model"], default="rules",
                           help="Execution mode (default: rules)")
    subparser.add_argument("--llm-base-url", help="LLM base URL (e.g. http://127.0.0.1:1234/v1)")
    subparser.add_argument("--llm-api-key", help="LLM API key (env: MCR_LLM_API_KEY)")
    subparser.add_argument("--llm-model", help="LLM model name (env: MCR_LLM_MODEL)")
    subparser.add_argument("--llm-timeout", type=float, help="LLM timeout in seconds (env: MCR_LLM_TIMEOUT_SECONDS)")
    subparser.add_argument("--llm-max-retries", type=int, help="LLM max retries (env: MCR_LLM_MAX_RETRIES)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcr",
        description="Market Capability Router",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser(
        "analyze",
        help="Analyze text, - for stdin, or @path for a UTF-8 file",
    )
    analyze.add_argument("text", help="Problem text, - for stdin, or @path")
    _add_llm_flags(analyze)
    analyze.set_defaults(func=cmd_analyze)

    candidate = sub.add_parser(
        "candidate",
        help="Evaluate candidate JSON from a file or stdin",
    )
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
    try:
        return args.func(args)
    except Exception as exc:
        print(f"mcr: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

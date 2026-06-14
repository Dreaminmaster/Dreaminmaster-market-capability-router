# Changelog

## 0.2.0 - 2026-06-14

- Added provider-independent LLM adapter protocol and response model.
- Added structured-output schema (v0.2) with field validation and injection detection.
- Added OpenAI-compatible adapter using stdlib (no external deps).
- Added deterministic FakeAdapter for CI/testing with fixture responses.
- Added configuration layer with precedence: CLI flag > env var > default (config file deferred).
- Added sensitive-data redaction before model calls.
- Added prompt-injection detection and data-envelope isolation.
- Added deterministic hybrid merge engine with provenance tracking.
- Added `--mode rules|hybrid|model` CLI flags with backward-compatible defaults.
- Added `--llm-*` CLI flags for base_url, model, timeout, retries.
- Engine preserves rules mode as default; hybrid falls back to rules on failure.
- Critical risk, SELF, and OFFICIAL routes cannot be overridden by model.
- Model-generated terms kept as candidates; never auto-entered into verified seed.
- Expanded product evaluations from 10 to 32 cases.
- Total unit tests: 89 (17 legacy + 72 new across 5 test files).
- Updated Skill and integration docs for v0.2 CLI patterns.

## 0.1.1 - 2026-06-14

- Added an OpenMinis-specific direct CLI integration path.
- Added candidate JSON input from stdin with `mcr candidate -`.
- Added safe text input through stdin or `@file` with `mcr analyze`.
- Added OpenMinis prerequisite smoke checks and live-trigger acceptance criteria.
- Clarified that installed Skill files do not by themselves prove runtime invocation.

## 0.1.0 - 2026-06-14

- Added complete product specification and architecture documents.
- Added installable Agent Skill.
- Added local-first Python reference implementation.
- Added seed knowledge for friction types, professions, platform terms, service standards, and risk rules.
- Added candidate scoring, query lattice generation, routing, risk checks, outcome storage, tests, and evaluation cases.
- Added coding-agent execution plan and acceptance criteria.

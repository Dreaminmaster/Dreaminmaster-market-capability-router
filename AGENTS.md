# Instructions for Coding Agents

## Product invariant

This repository implements a capability router, not a marketplace scraper and not a generic search assistant. Every feature must preserve the chain:

```text
user problem -> real goal -> friction -> task decomposition -> capability routing
-> market discovery when justified -> dialect interpretation -> candidate validation
-> user confirmation -> outcome learning
```

## Read first

1. `docs/PRODUCT_SPEC.md`
2. `docs/ARCHITECTURE.md`
3. `docs/CAPABILITY_ROUTING.md`
4. `docs/PLATFORM_DIALECT_ENGINE.md`
5. `docs/RISK_MODEL.md`
6. `docs/ACCEPTANCE_CRITERIA.md`
7. `plan/task_list.md`

## Required workflow

1. Read the current task and decision log.
2. Inspect existing code and tests.
3. Make the smallest coherent change.
4. Run `make all`.
5. Update tests, docs, changelog, and `plan/progress.md`.
6. Never silently weaken safety rules to make tests pass.

## Forbidden shortcuts

- Do not treat all problems as market-search tasks.
- Do not recommend full-service outsourcing before lower-risk diagnosis or review.
- Do not merge relevance and risk into one score.
- Do not convert uncertain dialect guesses into confirmed meanings.
- Do not generate code or terms intended to bypass platform moderation.
- Do not store raw credentials, verification codes, identity documents, or payment secrets.

## Architecture constraints

- Core domain logic remains provider-independent.
- External search, browser, OCR, image, and LLM integrations use adapters.
- Structured evidence accompanies every conclusion.
- Rules and seed data must be versioned and testable.
- Human approval gates protect account access, payments, submissions, and sensitive data.

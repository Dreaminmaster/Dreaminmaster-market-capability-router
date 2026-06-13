# Contributing

Before changing code, read `AGENTS.md`, `docs/PRODUCT_SPEC.md`, and `docs/ACCEPTANCE_CRITERIA.md`.

## Rules

1. Do not reduce the system to a generic keyword generator.
2. Keep reasoning evidence visible in structured outputs.
3. Separate service relevance from service risk.
4. Never add functionality intended to evade platform moderation or obtain prohibited services.
5. Add or update tests for every routing, dialect, scoring, or safety change.
6. Record important product decisions in `plan/decisions.md`.

## Pull request checklist

- [ ] Tests pass.
- [ ] Seed data validates.
- [ ] At least one evaluation case covers the change.
- [ ] No new sensitive data is stored by default.
- [ ] Documentation and changelog are updated.

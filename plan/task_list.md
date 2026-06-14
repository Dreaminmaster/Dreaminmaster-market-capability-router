# Task List for Coding Agents

## Completed in v0.1

- [x] Product specification
- [x] Architecture and routing rules
- [x] Platform dialect policy
- [x] Risk model
- [x] Data model
- [x] Installable Skill
- [x] Python CLI reference implementation
- [x] Seed data
- [x] Candidate evaluation
- [x] Outcome JSONL store
- [x] Tests and evaluation cases
- [x] GitHub Actions CI
- [x] OpenMinis direct CLI integration and live-trigger verification

## Active: v0.2 structured model adapter

Read `docs/V0.2_IMPLEMENTATION_SPEC.md` before changing code. Implement in the following order and keep each phase independently testable.

### Phase 1 — interfaces and configuration

- [ ] Define provider-independent `LLMAdapter` and `LLMResponse`
- [ ] Add versioned structured-output schema
- [ ] Add configuration precedence: CLI > environment > config > default
- [ ] Preserve rules-only default and backward-compatible CLI
- [ ] Add fake adapter and initial unit tests

### Phase 2 — OpenAI-compatible transport

- [ ] Implement configurable OpenAI-compatible adapter
- [ ] Support local endpoints such as LM Studio without requiring an API key
- [ ] Add mandatory timeout and bounded retry policy
- [ ] Redact secrets from errors and logs
- [ ] Add deterministic transport fixtures and tests

### Phase 3 — security and validation

- [ ] Treat user, listing, review, and chat content as untrusted data
- [ ] Add sensitive-data redaction before model calls
- [ ] Add prompt-injection detection and warning records
- [ ] Reject malformed or oversized structured output
- [ ] Reject unknown friction and route values
- [ ] Confirm rules mode never calls the model

### Phase 4 — deterministic hybrid merge

- [ ] Run rules and hard-risk scan before model enrichment
- [ ] Preserve critical risk, OFFICIAL, and SELF decisions
- [ ] Add provenance, confidence, status, and conflicts to enriched items
- [ ] Keep model vocabulary and dialect meanings as candidates
- [ ] Fall back to rules on all model failures
- [ ] Add conflict and failure tests

### Phase 5 — CLI, Skill, and OpenMinis

- [ ] Add `--mode rules|hybrid`
- [ ] Add provider/base URL/model/timeout configuration flags
- [ ] Update Skill runtime instructions
- [ ] Add rules-mode and hybrid-mode OpenMinis smoke tests
- [ ] Avoid unnecessary model calls for simple writing tasks
- [ ] Keep direct CLI invocation as the recommended OpenMinis path

### Phase 6 — evaluation and release

- [ ] Expand product evaluations from 10 to at least 30 cases
- [ ] Include prompt injection, model failure, multilingual, conflict, and false-trigger cases
- [ ] Run all legacy and new tests
- [ ] Update `CHANGELOG.md`
- [ ] Update `plan/progress.md`
- [ ] Update `plan/decisions.md`
- [ ] Update `docs/ACCEPTANCE_CRITERIA.md`
- [ ] Update `plan/test_report.md`
- [ ] Submit an implementation report with exact commands and commit SHA

## Next: v0.3 screenshot review

- [ ] Define `VisionAdapter`
- [ ] Extract title, description, price, service menu and chat statements
- [ ] Detect price-type ambiguity and image/text mismatch
- [ ] Preserve source regions for evidence
- [ ] Add redaction before persistence
- [ ] Add screenshot evaluation dataset with synthetic examples

## Next: v0.4 assisted browser

- [ ] Define browser action policy and user approval gates
- [ ] Generate multi-query search plan
- [ ] Normalize candidate pages
- [ ] Never automate password, verification code, payment, signature, or final submission
- [ ] Add complete action audit log

## Release gates

Before each release, run `make all` and update:

- `CHANGELOG.md`
- `plan/progress.md`
- `plan/decisions.md`
- `docs/ACCEPTANCE_CRITERIA.md`

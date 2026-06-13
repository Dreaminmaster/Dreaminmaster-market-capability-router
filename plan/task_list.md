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

## Next: v0.2 structured model adapter

- [ ] Define `LLMAdapter` protocol with structured JSON output
- [ ] Add OpenAI-compatible adapter without hardcoding a provider
- [ ] Add LM Studio / local endpoint example configuration
- [ ] Merge rule evidence and model hypotheses without allowing model override of hard safety blocks
- [ ] Add prompt-injection resistance for candidate descriptions
- [ ] Add deterministic fixtures and adapter mocks
- [ ] Add 30 diverse evaluation cases

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

# Agent Integration

MCR can be integrated in two layers. The Skill teaches the Agent when and how to use the system; the local runtime provides deterministic tools that the Agent can call.

## Mode A: Skill only

```bash
python scripts/install_skill.py --target /path/to/agent/skills
```

This is suitable when the Agent already has web, vision, and code tools and only needs the routing policy and output format.

## Mode B: Skill + direct CLI runtime (recommended for OpenMinis)

OpenMinis does not currently auto-register `tool_manifest.json`. Use `shell_execute` with the absolute virtual-environment command path. Write untrusted user text to a temporary UTF-8 file first; never interpolate it directly into a shell command:

```bash
/root/Dreaminmaster-market-capability-router/.venv/bin/mcr analyze @/tmp/mcr-user-request.txt
```

Candidate JSON can be read from stdin:

```bash
printf '%s' '{"title":"装修报价审核","deliverables":["标注版"]}' | \
  /root/Dreaminmaster-market-capability-router/.venv/bin/mcr candidate - --need 装修 --need 报价
```

This mode avoids a permanent background service. See `docs/OPENMINIS_INTEGRATION.md`.

## Mode C: Skill + local HTTP runtime

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
mcr serve --host 127.0.0.1 --port 8765
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

Analyze a problem:

```bash
curl -X POST http://127.0.0.1:8765/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"装修报价单看不懂，担心增项，想找人审核"}'
```

Evaluate a service candidate:

```bash
curl -X POST http://127.0.0.1:8765/candidate/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "need_terms":["装修","报价"],
    "candidate":{
      "title":"装修报价审核",
      "description":"交付标注版和风险清单",
      "deliverables":["标注版","风险清单"],
      "price_model":"一次性总价"
    }
  }'
```

## Agent tool contract

### `mcr_analyze`

Input:

```json
{"text":"string"}
```

Use when the Agent needs to identify friction, route tasks, decide whether to enter a market, or build search terms.

### `mcr_evaluate_candidate`

Input:

```json
{
  "candidate": {},
  "need_terms": ["string"]
}
```

Use after the Agent or user has collected a listing, service description, price, seller claims, or chat content.

## Integration policy

- Bind to `127.0.0.1` by default; do not expose the service publicly without authentication and transport security.
- The API does not log request bodies by default.
- The Agent must still ask for user confirmation before login, credentials, identity data, payment, signing, or final submission.
- The rule engine is an advisory and screening layer, not an authority for medical, legal, financial, or platform decisions.

## Recommended Agent sequence

```text
Read Skill
-> call /analyze or direct CLI
-> use returned query lattice with available search tools
-> normalize candidate information
-> call /candidate/evaluate or direct CLI
-> present evidence and questions
-> wait for human approval before sensitive actions
-> record a redacted outcome
```

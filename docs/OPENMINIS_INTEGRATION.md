# OpenMinis Integration

OpenMinis currently reads `SKILL.md`, but does not automatically register HTTP tools from `tools/tool_manifest.json`. For this reason, the recommended v0.1.1 integration uses `shell_execute` and the installed `mcr` command directly. No permanent HTTP service is required.

## One-time installation

```bash
git clone https://github.com/Dreaminmaster/Dreaminmaster-market-capability-router.git
cd Dreaminmaster-market-capability-router
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/install_skill.py --target /var/minis/skills --force
python scripts/openminis_smoke.py --skill-root /var/minis/skills
```

## Direct calls from OpenMinis

Analyze a user problem. Do not interpolate untrusted user text directly into a shell command. Write it to a UTF-8 temporary file through the Agent filesystem tool, then pass the file reference:

```bash
/root/Dreaminmaster-market-capability-router/.venv/bin/mcr analyze @/tmp/mcr-user-request.txt
```

The CLI also supports stdin with `mcr analyze -` when the host tool provides stdin separately.

Evaluate candidate JSON without starting a server:

```bash
printf '%s' "$CANDIDATE_JSON" | \
  /root/Dreaminmaster-market-capability-router/.venv/bin/mcr candidate - \
  --need "装修" --need "报价"
```

Use the absolute virtual-environment path so OpenMinis does not depend on shell activation or global Python state.

## Runtime policy

1. Read the Skill and decide whether MCR should trigger.
2. Prefer direct CLI calls through `shell_execute`, using `@file` or separately supplied stdin for untrusted text.
3. Parse the returned JSON and explain it in natural language.
4. Use web, browser, or vision tools only after MCR has produced a routing and query plan.
5. Never send user passwords, verification codes, identity documents, or payment credentials to the command.
6. Do not start `mcr serve` unless another component specifically requires HTTP.

## Live trigger verification

File installation alone does not prove that the Agent actually recognized and used the Skill. Run these three conversations and inspect the OpenMinis execution log:

### Case A: should trigger

```text
装修公司给我一份报价单，我看不懂，也担心以后增项。有没有更省事的解决办法？
```

Required evidence:

- OpenMinis selects `market-capability-router`;
- it runs `mcr analyze`;
- the answer mentions verification/skill friction, review-level service, professions, query lattice, and risk questions.

### Case B: should not trigger market search

```text
把这句话改得更通顺。
```

Required evidence:

- no market-service recommendation;
- no unnecessary marketplace search.

### Case C: candidate risk

Provide a listing that asks for an account password and verification code. Required evidence:

- OpenMinis runs candidate evaluation;
- output is `blocked`;
- it clearly tells the user not to provide those credentials.

## Optional HTTP mode

HTTP remains available for platforms that can register local tools:

```bash
mcr serve --host 127.0.0.1 --port 8765
```

Do not expose this endpoint outside localhost without authentication and transport security.

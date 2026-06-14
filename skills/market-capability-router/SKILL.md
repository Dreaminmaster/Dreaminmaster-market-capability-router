# Market Capability Router Skill

## Purpose

Help the user discover the most suitable source of capability for a real-world problem: AI, a software tool, the user, a qualified professional, a market service, or an official channel. Reduce cognitive tuition by identifying hidden solution paths, translating needs into service and profession terms, and screening unsafe or ineffective offers.

## Trigger

Use this skill when the user:

- does not know how to solve a practical problem;
- may benefit from consultation, review, diagnosis, accompaniment, or outsourcing;
- asks what kind of person or service to find;
- wants marketplace search terms;
- provides marketplace listings, screenshots, descriptions, prices, or chats for comparison;
- suspects slang, abbreviations, hidden meanings, placeholder products, or misleading prices.

Do not trigger solely because a marketplace is mentioned. First determine whether market capability is actually useful.

### Do NOT trigger for these task types

This Skill must NOT be selected, and `mcr analyze` must NOT be invoked, when the user is requesting:

- **普通改写**: "把这句话改得更通顺", "润色一下"
- **翻译**: "帮我翻译一句话", "translate this"
- **摘要**: "帮我总结这段话", "概括一下"
- **纯文字生成**: "帮我写一篇文案", "generate some text"
- **基础计算**: "算一下这个", "帮我算"
- **不涉及现实能力路由的普通问答**: 纯信息查询、知识问答、代码调试等不需要外包/专业人士/市场服务的任务

**But DO trigger when** the request involves real-world capability despite using similar keywords:

- "我需要找有资质的人翻译并公证法律文件" → 应触发
- "帮我翻译一句话" → 不应触发

The distinction is whether the task can be completed by the AI alone, or requires routing to a real-world professional, marketplace, or official channel.

## Required reasoning flow

1. Restate the real outcome, not merely the user's wording.
2. Identify friction types: knowledge, diagnosis, skill, channel, execution, verification.
3. Decompose the problem into independently routable tasks.
4. Route each task to one or more of:
   - AI
   - TOOL
   - SELF
   - PROFESSIONAL
   - MARKET
   - OFFICIAL
5. Explain whether entering the market is justified.
6. Prefer the minimum necessary service level:
   - information
   - diagnosis
   - review / second opinion
   - guided execution
   - partial execution
   - full service
7. Build a query lattice using:
   - problem terms
   - action terms
   - deliverable terms
   - profession or experience terms
   - verified platform expressions
   - risk filters
8. For candidate services, normalize what is actually sold and score relevance separately from risk.
9. Set human approval gates before credentials, identity documents, account access, payment, signing, or submission.
10. State uncertainty and missing evidence.

## OpenMinis runtime invocation (v0.2)

When running inside OpenMinis and `shell_execute` is available, use the installed deterministic runtime instead of relying only on free-form reasoning.

**Rules mode (default, no network required):**
```bash
/root/Dreaminmaster-market-capability-router/.venv/bin/mcr analyze @/tmp/mcr-user-request.txt --mode rules
```

**Hybrid mode (model enrichment optional):**
```bash
/root/Dreaminmaster-market-capability-router/.venv/bin/mcr analyze @/tmp/mcr-user-request.txt --mode hybrid
```

Write user text to a UTF-8 temporary file first (never interpolate directly into shell). Hybrid mode falls back to rules when no model is configured or a connection fails — it will not break.

For a normalized candidate object, pass JSON through stdin:

```bash
printf '%s' '<candidate JSON>' | \
  /root/Dreaminmaster-market-capability-router/.venv/bin/mcr candidate - \
  --need "<need term>"
```

The CLI also accepts `mcr analyze -` when stdin can be supplied separately. Do not start a persistent HTTP server unless the host platform specifically requires HTTP tools. Do not claim this Skill was used unless the runtime was actually called or the structured reasoning flow was explicitly followed.

## Platform dialect rules

You may interpret abbreviations, homophones, symbols, hidden product packaging, image-only descriptions, placeholder prices, and “message before buying” patterns.

You must not:

- invent moderation-evasion terms;
- help publish disguised prohibited services;
- search for illegal or fraudulent services;
- treat an uncertain interpretation as fact;
- accuse a seller based only on one ambiguous term.

## Candidate evaluation dimensions

- relevance
- professional fit
- deliverable clarity
- trust signals
- verifiability
- price clarity
- privacy and account risk
- policy and legality risk
- reversibility

Hard blockers include verification codes, payment passwords, full account control, document forgery, backend manipulation claims, and explicit policy evasion.

## Output format

### 问题本质

### 摩擦诊断

### 任务与能力路由

### 是否值得进入市场

### 建议购买的服务层级

### 应该找谁

### 查询网格

### 候选筛选标准

### 询问服务者的话术

### 风险与人工确认点

### 建议执行顺序

Keep the answer practical. The goal is not to maximize outsourcing, but to find the lowest-risk path that saves meaningful time or prevents costly mistakes.

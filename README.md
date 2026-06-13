# Market Capability Router

> AI + Tool + Human + Market Capability Router
>
> 把“我不知道怎么办”翻译成：缺什么能力、该由谁处理、市场上叫什么、去哪里找、怎样验证，以及是否值得购买。

[中文](#中文说明) · [English](#english-summary)

## 中文说明

Market Capability Router（MCR）是一套面向现实问题的能力发现、路由、搜索与风险验证系统。它不是简单的“闲鱼关键词生成器”，而是先诊断用户遇到的摩擦，再把任务分配给最合适的能力来源：

- AI：解释、整理、初步分析；
- Tool：搜索、计算、文件解析、自动化；
- Human：用户本人或专业人士；
- Market：可购买的咨询、审核、诊断、陪跑或执行服务；
- Official：官方平台、机构和正式申诉渠道。

系统尤其关注用户常常不知道的“未知解决路径”：装修报价可以找独立审核，账号申诉可以先做原因诊断，酒店预订可以比较合法渠道，二手设备可以购买远程验机或第三方检测。

### 第一版能力

1. 识别知识、诊断、熟练度、渠道、执行、验证等认知摩擦；
2. 将任务路由到 AI、工具、本人、专业人士、市场服务或官方渠道；
3. 生成标准词、职业身份词、行业词、平台表达和风险过滤词组成的查询网格；
4. 识别平台简拼、谐音、隐晦表达、占位价格和图文不一致的候选信号；
5. 对候选服务进行相关度、专业度、交付清晰度、可信度和风险评分；
6. 记录真实结果，用于更新问题—能力—职业—服务映射。

### 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

mcr analyze "装修公司给了我一份报价单，我看不懂，也担心后续增项"
```

分析一个候选服务：

```bash
mcr candidate examples/candidates/account_service.json
```

运行测试：

```bash
python -m unittest discover -s tests -v
python scripts/validate_data.py
python scripts/run_evals.py
```

### 安装为 Agent Skill

```bash
python scripts/install_skill.py --target ~/.agents/skills
```

脚本只复制 `skills/market-capability-router`，不会修改 Agent 的其他配置。不同 Agent 的 Skill 目录不同，可通过 `--target` 指定。

### 目录

```text
market-capability-router/
├── docs/        产品规格、架构、路由、风险与验收标准
├── skills/      可安装给 Agent 的 Skill
├── src/mcr/     最小可运行原型
├── data/        种子数据与 JSON Schema
├── evals/       标准案例和期望结果
├── tests/       单元测试与端到端测试
├── scripts/     安装、诊断、数据校验与评测脚本
└── plan/        供编程 Agent 持续执行的任务与决策记录
```

### 安全边界

平台语言模块用于理解与筛选，不用于帮助规避平台审核、寻找违法服务、伪造身份材料或绕过实名与风控。系统对密码、验证码、支付控制权、所谓“内部渠道”和“百分之百成功”等信号提高风险等级。

### 当前状态

当前版本为 `v0.1.0`：完成产品规格、数据模式、规则型最小原型、Skill、测试与施工任务书。联网检索、浏览器自动化、图像理解和模型适配器保留为后续插件，不在第一版默认启用。

## English summary

Market Capability Router diagnoses the user's real friction, decomposes the task, and routes each step to AI, software tools, the user, qualified professionals, market services, or official channels. It also builds a query lattice, interprets marketplace dialect, evaluates service candidates, and records outcomes.

The first release is intentionally local-first and rule-based. External search, browser automation, OCR, image understanding, and LLM providers are extension points rather than hard dependencies.

## License

Source is currently provided for evaluation only. See `LICENSE`.

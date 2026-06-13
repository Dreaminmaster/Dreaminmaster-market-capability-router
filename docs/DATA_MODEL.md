# 数据模型

## Case

一次完整问题分析。

```text
case_id
created_at
user_goal
constraints
sensitivity
frictions[]
tasks[]
routes[]
queries[]
candidates[]
risk_flags[]
selected_path
outcome
```

## Friction

```text
friction_type
score
matched_signals[]
explanation
```

## Task

```text
task_id
title
input
expected_deliverable
failure_cost
requires_user_action
sensitivity
```

## RouteDecision

```text
task_id
primary_route
secondary_routes[]
market_stage
confidence
reasons[]
human_gate
```

## PlatformTerm

```text
term
canonical_concept
platform
expression_type
possible_services[]
risk_level
confidence
first_seen
last_verified
evidence_required[]
```

## Candidate

```text
candidate_id
raw_title
raw_description
listed_price
normalized_service
deliverables[]
provider_claims[]
required_data[]
price_model
signals[]
```

## CandidateEvaluation

```text
relevance
professionalism
deliverable_clarity
trust
verifiability
risk
status
reasons[]
questions[]
```

## Outcome

```text
case_id
chosen_route
chosen_service_level
query_used
money_spent
time_spent_hours
success
promise_matched
extra_charges
incidents[]
notes
```

## 版本与证据

所有知识条目必须包含：

- `version`；
- `source_type`；
- `confidence`；
- `last_verified`；
- `status`：candidate / verified / deprecated。

对于快速变化的平台黑话，`last_verified` 是强制字段。

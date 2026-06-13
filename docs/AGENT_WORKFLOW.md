# Agent 工作流与状态机

## 状态

```text
RECEIVED
  -> UNDERSTOOD
  -> DIAGNOSED
  -> DECOMPOSED
  -> ROUTED
  -> MARKET_DECISION
  -> QUERY_BUILT
  -> CANDIDATES_COLLECTED
  -> CANDIDATES_NORMALIZED
  -> EVALUATED
  -> HUMAN_CONFIRMATION
  -> EXECUTION_OBSERVED
  -> OUTCOME_RECORDED
```

任意状态可进入：

```text
NEED_USER_FACT
BLOCKED_BY_POLICY
INSUFFICIENT_EVIDENCE
OFFICIAL_ONLY
COMPLETED
```

## 标准运行步骤

1. 提取目标、预算、时间、所在地、已尝试方法和敏感度；
2. 诊断摩擦并给出证据；
3. 拆任务，不能把整个问题作为一个不可解释的整体；
4. 为每个任务路由；
5. 仅在满足进入市场条件时生成查询；
6. 优先推荐诊断、审核和第二意见；
7. 读取候选的标题、描述、图片、价格、评价和聊天；
8. 分离相关度和风险；
9. 生成针对候选的追问；
10. 在付款、账号、证件和提交前设置人工确认；
11. 记录脱敏结果。

## 工具调用策略

- 本地知识足够：不联网；
- 规则、价格、平台状态可能变化：调用搜索；
- 图片含主要信息：调用视觉或 OCR；
- 候选需要比较：先归一化再排序；
- 结论缺证据：标记不确定，不自动补全。

## 失败回退

- 搜索无结果：切换职业身份词和交付物词，不立即扩大到高风险暗语；
- 黑话不确定：输出多个假设并请求更多上下文；
- 市场候选均高风险：回退到官方或正规专业机构；
- 无法定义交付：停止购买建议，先帮助定义交付；
- 价格不可比较：要求拆分咨询费、定金和总价。

## 输出骨架

```text
问题本质
摩擦诊断
任务与路由
是否进入市场
建议购买层级
查询网格
候选判断
验证问题
风险与人工确认
下一步执行顺序
```

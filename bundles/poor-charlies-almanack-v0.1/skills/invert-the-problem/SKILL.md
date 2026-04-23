# Invert the Problem

## Identity
```yaml
skill_id: invert-the-problem
title: Invert the Problem
status: published
bundle_version: 0.1.0
skill_revision: 5
```

## Contract
```yaml
trigger:
  patterns:
    - user_planning_a_high_stakes_action_path
    - user_stuck_in_complex_success_planning
  exclusions:
    - user_request_is_pure_fact_lookup
    - user_outcome_is_already_decided
intake:
  required:
    - name: objective
      type: string
      description: Outcome the user wants to achieve.
    - name: constraints
      type: list
      description: Known constraints, irreversibilities, and deadlines.
judgment_schema:
  output:
    type: structured
    schema:
      failure_modes: list[string]
      avoid_rules: list[string]
      first_preventive_action: string
      edge_posture: enum[full_inversion, partial_review, defer]
  reasoning_chain_required: true
boundary:
  fails_when:
    - user_treats_inversion_as_complete_strategy_without_followup
    - input_lacks_a_concrete_objective_or_constraint_set
  do_not_fire_when:
    - user_request_is_pure_fact_lookup
    - user_outcome_is_already_decided
```

## Rationale
逆向思维不是一句“反过来想想看”的装饰性口号，而是先把失败路径写成地图，再决定值不值得往前冲。凡是用户出现“我总觉得漏掉了什么重要的东西”“这个方案太乐观了”“最坏的情况是什么”“帮我系统性找找漏洞”“怎么才能不血本无归”之类的信号，都应该先把正向目标翻成反面问题：什么会导致这件事彻底失败、不可恢复、或者把人拖进长期被动。[^anchor:invert-source-note]

输出也必须是结构化行动，而不是泛泛的风险提示。至少要产出三样东西：明确的 `failure_modes`，一组真正会改变决策边界的 `avoid_rules`，以及一条最先要执行的 `first_preventive_action`。如果用户连目标和约束都说不清，或者其实早就决定了，只是想让你帮他做一个“已经考虑过风险”的仪式，那就不该把逆向思维降级成空 checklist；应直接指出目标不清、致命失败未命名、或当前信息还不足以做安全优化。[^anchor:invert-eval] [^trace:canonical/anti-ruin-checklist.yaml]

## Evidence Summary
三条 canonical trace 定义了这条 skill 的执行方式。`anti-ruin-checklist` 对应最标准的用法：先列“会怎么死”，再决定值不值得谈成功路径。[^trace:canonical/anti-ruin-checklist.yaml] `pilot-pre-mortem` 说明逆向思维的产出不只是“担心”，而是把单点失败、激励错位、前提脆弱性提前暴露出来，让团队在承诺之前先补洞。[^trace:canonical/pilot-pre-mortem.yaml] `airline-bankruptcy-checklist` 则证明，在叙事再乐观、增长故事再漂亮的情况下，只要破产链条还没被切断，逆向思维就应强行把讨论拉回失败条件。[^trace:canonical/airline-bankruptcy-checklist.yaml]

这些证据共同支持一个判断：逆向思维真正有价值，不是因为它“听起来更深刻”，而是因为它能把“这个计划有什么漏洞”变成明确的 no-go condition、避坑规则和第一步补救动作。[^anchor:invert-source-note] [^anchor:invert-eval]

## Relations
```yaml
depends_on: []
delegates_to:
  - bias-self-audit
constrained_by:
  - circle-of-competence
complements:
  - margin-of-safety-sizing
  - opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
当前挂载 trace：3 条。

代表性案例：
- `traces/canonical/anti-ruin-checklist.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`
- `traces/canonical/airline-bankruptcy-checklist.yaml`

推荐输出骨架：
1. 先把问题翻转成反面：例如“什么会导致这个产品上市彻底失败 / 这次扩张最坏会死在哪 / 这笔投资在什么条件下会血本无归”。
2. 至少列出 5 条具体失败路径，覆盖目标混乱、单点依赖、资源断裂、激励扭曲、外部约束等维度。
3. 给每条失败路径标注严重度与触发条件，识别致命、不可恢复的失败。
4. 输出 `avoid_rules`、`first_preventive_action`，并标注 `edge_posture`：重大高风险场景用 `full_inversion`，边界场景可降级为 `partial_review`，不适合的方法论场景直接 `defer`。

高频触发场景包括：上市计划、跨市场扩张、创业方案、投资决策、以及团队只看到机会看不到威胁的时候。
像“跳槽要不要去”“健身计划怎么做”这类边界案例，只有在用户明确要求看失败模式、且方法论收益大于复杂度时，才适合 `partial_review`；否则应 `defer` 给一般决策辅助。

## Evaluation Summary
KiU Test 当前为 green，并继续绑定完整的 v0.1 shared evaluation corpus。当前摘要覆盖 20 条真实决策、20 条 adversarial trap、10 条 OOD refusal；主要失败簇是“正向计划说得很完整，但从没命名 ruin path”，以及“行动早就决定了，才来补一个逆向分析的样子货”。

边界要求必须明确写进产出：
- 纯概念查询，例如“逆向思维是什么意思”，不触发。
- 纯创意发散，例如“帮我头脑风暴几个方向”，不触发，因为这时需要的是扩张而不是防御。
- 边界案例可以按权重触发，例如跳槽分析、健身计划；前提是用户真的要看失败模式，而不是泛泛比较优劣。

详见 `eval/summary.yaml`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。本轮把正文改成中文 action-facing 说明，明确补进了“漏掉重要东西 / 方案太乐观 / 最坏情况 / 系统性找茬 / 血本无归”等触发语言，并把输出落成 failure map、avoid rules、first preventive action 三件套。

同时，这轮也把 concept query、pure brainstorming、低风险边界案例的裁定说明写清楚，并显式加入 `edge_posture = full_inversion / partial_review / defer`，避免通过过度泛化触发来换 benchmark 分数。剩余缺口是继续提高 edge case 的边界稳定性，并补出真实 loop 驱动的修订证据。详见 `iterations/revisions.yaml`。

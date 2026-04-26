# Invert the Problem

## Identity
```yaml
skill_id: invert-the-problem
title: Invert the Problem
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 1
```

## Contract
```yaml
trigger:
  patterns:
  - user_planning_a_high_stakes_action_path
  - user_stuck_in_complex_success_planning
  exclusions:
  - user_request_is_pure_fact_lookup
  - user_request_is_concept_definition_or_history_query
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
  - user_only_wants_concept_explanation_or_historical_examples
  do_not_fire_when:
  - user_request_is_pure_fact_lookup
  - user_request_is_concept_definition_or_history_query
  - user_outcome_is_already_decided
```

## Rationale
逆向思维不是一句“反过来想想看”的装饰性口号，而是先把失败路径写成地图，再决定值不值得往前冲。凡是用户出现“我总觉得漏掉了什么重要的东西”“这个方案太乐观了”“最坏的情况是什么”“帮我系统性找找漏洞”“怎么才能不血本无归”之类的信号，都应该先把正向目标翻成反面问题：什么会导致这件事彻底失败、不可恢复、或者把人拖进长期被动。[^anchor:invert-source-note]

输出也必须是结构化行动，而不是泛泛的风险提示。至少要产出三样东西：明确的 `failure_modes`，一组真正会改变决策边界的 `avoid_rules`，以及一条最先要执行的 `first_preventive_action`。如果用户连目标和约束都说不清，或者其实早就决定了，只是想让你帮他做一个“已经考虑过风险”的仪式，那就不该把逆向思维降级成空 checklist；应直接指出目标不清、致命失败未命名、或当前信息还不足以做安全优化。[^anchor:invert-eval] [^trace:canonical/anti-ruin-checklist.yaml]

## Evidence Summary
三条 canonical trace 定义了这条 skill 的执行方式。`anti-ruin-checklist` 对应最标准的用法：先列“会怎么死”，再决定值不值得谈成功路径。[^trace:canonical/anti-ruin-checklist.yaml] `pilot-pre-mortem` 说明逆向思维的产出不只是“担心”，而是把单点失败、激励错位、前提脆弱性提前暴露出来，让团队在承诺之前先补洞。[^trace:canonical/pilot-pre-mortem.yaml] `airline-bankruptcy-checklist` 则证明，在叙事再乐观、增长故事再漂亮的情况下，只要破产链条还没被切断，逆向思维就应强行把讨论拉回失败条件。[^trace:canonical/airline-bankruptcy-checklist.yaml]

这些证据共同支持一个判断：逆向思维真正有价值，不是因为它“听起来更深刻”，而是因为它能把“这个计划有什么漏洞”变成明确的 no-go condition、避坑规则和第一步补救动作。[^anchor:invert-source-note] [^anchor:invert-eval]

The v0.2 seed preserves graph/source double anchoring and records the workflow-vs-agentic routing decision in `candidate.yaml`.

Scenario-family anchor coverage: `should_trigger` `failure-first-planning` -> `invert-source-note`, `invert-trace-airline` (这是典型的 failure-first 评估窗口，而不是普通创意讨论。); `should_trigger` `team-red-team-review` -> `invert-trace-pilot`, `invert-eval` (这类场景需要显式把乐观方案翻译成失败条件，而不是继续扩创意广度。); `should_not_trigger` `pure-brainstorming` -> `invert-source-note` (逆向思维是保守和防御型工具，不适合拿来替代 ideation。); `should_not_trigger` `concept-definition-query` -> `invert-source-note` (这类请求只是在问概念解释或历史案例，没有真实待决目标、约束和失败路径。); `edge_case` `medium-stakes-personal-decision` -> `invert-eval`, `invert-real-decision` (这类场景可以做轻量 failure scan，但不应该被升级成重大资本配置级框架。); `refusal` `post-hoc-decoration` -> `invert-source-note` (inversion 应该改变决策路径，不应给既定结论补礼貌性风险词。).

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_error_avoidance`/Error avoidance; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 把目标翻成 failure map：列 failure_modes、avoid_rules、first_preventive_action，并决定 full_inversion / partial_review / defer。

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
Current trace attachments: 3.

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_error_avoidance`/Error avoidance; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 把目标翻成 failure map：列 failure_modes、avoid_rules、first_preventive_action，并决定 full_inversion / partial_review / defer。

Scenario families:
- `should_trigger` `failure-first-planning`; 当用户主动问“这个计划怎么失败”“最坏会怎样”“有什么漏洞”时触发。; signals: 最坏会怎样 / 有什么漏洞 / 怎么会失败; boundary: 这是典型的 failure-first 评估窗口，而不是普通创意讨论。; next: 列出 failure modes、avoid rules、找茬清单和 first preventive action，再决定 full_inversion / partial_review / defer。
- `should_trigger` `team-red-team-review`; 当团队只看到了机会没看到威胁，希望做系统性红队审查时触发。; signals: 只看到了机会没看到威胁 / 系统性找找茬 / 帮我做 pre-mortem; boundary: 这类场景需要显式把乐观方案翻译成失败条件，而不是继续扩创意广度。; next: 输出潜在威胁、失败模式、找茬清单和预防动作，避免只给一句“注意风险”。
- `should_trigger` `graph-inferred-link-e_invert_margin_complements`; Graph-to-skill distillation: `INFERRED` edge `e_invert_margin_complements` expands trigger language only when a live decision links `Invert the problem` and `Margin of safety sizing`.; signals: Invert the problem / Margin of safety sizing / # Invert the Problem Source Note Skill ID: invert-the-problem Primary Claim:...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 把目标翻成 failure map：列 failure_modes、avoid_rules、first_preventive_action，并决定 full_inversion / partial_review / defer。 Evidence check: verify source_location `sources/invert-the-problem.md:1-9` before expanding the trigger.
- `should_not_trigger` `pure-brainstorming`; 纯头脑风暴或创意发散不应触发。; signals: 头脑风暴 / 创意方向 / 新产品点子; boundary: 逆向思维是保守和防御型工具，不适合拿来替代 ideation。
- `should_not_trigger` `concept-definition-query`; 纯概念定义、历史来源或例子解释不应触发。; signals: 逆向思维是什么意思 / 反过来想有哪些例子 / 芒格为什么强调 inversion; boundary: 这类请求只是在问概念解释或历史案例，没有真实待决目标、约束和失败路径。
- `edge_case` `medium-stakes-personal-decision`; 跳槽、搬家、个人计划等中等复杂度决策，只有当用户明确要求扫描失败模式时才部分触发。; signals: 跳槽会不会踩坑 / 有没有没想到的风险 / 想先做个 pre-mortem; boundary: 这类场景可以做轻量 failure scan，但不应该被升级成重大资本配置级框架。; next: 先确认是不是在做 failure scan，再给轻量 pre-mortem 与 partial_review，而不是过度重型化。
- `refusal` `post-hoc-decoration`; 当结论已经锁死、用户只想事后补一层“逆向思考”装饰时拒绝。; signals: 已经决定了 / 只是想再确认一下 / 帮我补充几个风险点; boundary: inversion 应该改变决策路径，不应给既定结论补礼貌性风险词。; next: 明确指出当前更适合执行复盘或一般风险提示，而不是伪装成 full_inversion。

Representative cases:
- `traces/canonical/anti-ruin-checklist.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`
- `traces/canonical/airline-bankruptcy-checklist.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=20 / total=20, threshold=0.7, status=`pass`
- `synthetic_adversarial`: passed=20 / total=20, threshold=0.85, status=`pass`
- `out_of_distribution`: passed=10 / total=10, threshold=0.9, status=`pass`

关键失败模式：
- Inversion can become vague advice unless it outputs explicit avoid-rules.
- Already-decided actions can misuse inversion as decorative post-hoc reasoning unless boundary rules reject them.
- Forward plans can sound coherent while leaving single-point failures and survival constraints unnamed.
- Concept, definition, and history-example prompts can look semantically related but must not trigger without a live decision objective.

场景族覆盖：`should_trigger`=3，`should_not_trigger`=2，`edge_case`=1，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Revision 6 是一次面向 `v0.6.0` same-source boundary cleanup 的手工补强，不是 refinement_scheduler 自动 loop。本轮明确把 concept / definition / history query 排除在 inversion 触发外，避免把“解释逆向思维概念”误判成“帮助真实决策做 failure-first planning”。

Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。本轮把正文改成中文 action-facing 说明，明确补进了“漏掉重要东西 / 方案太乐观 / 最坏情况 / 系统性找茬 / 血本无归”等触发语言，并把输出落成 failure map、avoid rules、first preventive action 三件套。

同时，这轮也把 concept query、pure brainstorming、低风险边界案例的裁定说明写清楚，并显式加入 `edge_posture = full_inversion / partial_review / defer`，避免通过过度泛化触发来换 benchmark 分数。剩余缺口是继续提高 edge case 的边界稳定性，并补出真实 loop 驱动的修订证据。详见 `iterations/revisions.yaml`。

本轮补入：
- Added direct Chinese trigger phrases such as "漏掉了什么重要的东西", "方案太乐观", "最坏的情况", and "系统性找茬".
- Reworked the usage and evaluation summaries around explicit failure maps, avoid rules, and first preventive actions.
- Clarified non-trigger boundaries for concept queries, pure brainstorming, and lower-stakes edge cases without broadening the skill boundary.

当前待补缺口：
- Continue monitoring concept-query and low-stakes planning boundary stability in same-source benchmarks.
- Run a real refinement_scheduler pass before describing this skill as loop-driven.

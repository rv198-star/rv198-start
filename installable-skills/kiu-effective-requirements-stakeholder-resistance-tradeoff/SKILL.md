---
name: kiu-effective-requirements-stakeholder-resistance-tradeoff
description: Use this KiU-generated action skill from Effective Requirements Analysis when the task matches `stakeholder-resistance-tradeoff`.
---

# Stakeholder Resistance Tradeoff

## Identity
```yaml
skill_id: stakeholder-resistance-tradeoff
title: Stakeholder Resistance Tradeoff
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - stakeholder_attention_and_resistance_conflict
  - important_stakeholder_missing_from_requirement
  - scope_choice_depends_on_power_interest_tradeoff
  exclusions:
  - stakeholder_list_is_only_being_filled
  - single_stakeholder_no_conflict
  - concept_query_only
intake:
  required:
  - name: stakeholders
    type: list[structured]
    description: 关键干系人、角色、权力、受影响程度和使用关系。
  - name: attention_points
    type: list[string]
    description: 各干系人的关注点、成功标准或收益。
  - name: resistance_points
    type: list[string]
    description: 各干系人的担心、阻力点、损失或反对理由。
  - name: decision_scope
    type: string
    description: 当前要决定的需求范围、优先级或沟通策略。
  - name: disconfirming_evidence
    type: list[string]
    description: 证明某个干系人被漏掉、权力判断错误或阻力被低估的证据。
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[prioritize_resistance|prioritize_attention|ask_for_missing_stakeholder|defer]
      critical_stakeholders: list[string]
      tradeoff_reason: string
      risk_if_ignored: list[string]
      evidence_to_check: list[string]
      next_action: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - critical_stakeholder_identity_uncertain
  - resistance_point_is_asserted_without_evidence
  do_not_fire_when:
  - stakeholder_list_is_only_being_filled
  - single_stakeholder_no_conflict
```

## Rationale
`Stakeholder Resistance Tradeoff` is anchored in "### 5 干系人分析"[^anchor:5-干系人分析-principle::0012]. `识别出关键干系人只是第一步，选择合适的代表进行调研，分析他们的关注点、阻力点，以及满足关注点、避免阻力点所需的功能、非功能需求也是一个重要...` adds source context through "识别出关键干系人只是第一步，选择合适的代表进行调研，分析他们的关注点、阻力点，以及满足关注点、避免阻力点所需的功能、非功能需求也是一个重要任务。 干系人分析任务执行指引如图5-1所示。"[^anchor:5-干系人分析-evidence::effective-requirements-0032]. `很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...` adds source context through "很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需求”这个概念，是执行好该任务的关键。 干系人负需求 案例分析 很多年前，我参与了一些电子政务系统的开发，在一次省、市、县三级的“效能监管系统”项目中遇到了一件有趣的事情。 这个项目首先在省厅进行了需求调研，调研告一段落后，省厅领导让我们到A市——他们最有代表性的一个地级市进行深入调研。 去的那天，路上"[^anchor:5-干系人分析-evidence::effective-requirements-0033]. This candidate exists because stakeholder analysis becomes agentic when the work is no longer listing roles but judging whose concern, resistance, or missing voice should change scope and next action. The deterministic stakeholder workflow remains the right artifact for inventory building; this skill handles conflict-sensitive boundary arbitration. The output must name the evidence it checked, the boundary reason, and a concrete next action; otherwise it should defer or route back to workflow_candidates/.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...` — 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)按KPI分解：KPI指标体系通常直接体现了管理者的核心关注点，因此可以事先进行收集、归类，然后逐一切入，以发现潜在的关注点和阻力点。 (2)按工作主题分解：管理者通常会涉及多个不同的工作主题，如负责物资供应的经理会涉及领用、采购、仓储等不同主题。事先梳理出被访谈对象的工作主题，以便访谈时分而治之。 ([^anchor:stakeholder-resistance-tradeoff-case::effective-requirements-0034]
- mechanism observed: `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...` contains mechanism-density `0.75`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Stakeholder Resistance Tradeoff` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `stakeholder_attention_and_resistance_conflict`
- anti-misuse boundary: `stakeholder_list_is_only_being_filled`

### Downstream Use Check
This skill must make `Stakeholder Resistance Tradeoff` decision-relevant by naming the main tension, the current action it changes, and the boundary that prevents treating every disagreement as the same problem.

Minimum Pressure Pass (alternative pressure): Test one competing problem frame before applying the skill; if a different tension better explains the situation, return that reframing or defer instead of forcing the original frame. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Stakeholder Resistance Tradeoff` is grounded in "### 5 干系人分析"[^anchor:5-干系人分析-principle::0012].

`识别出关键干系人只是第一步，选择合适的代表进行调研，分析他们的关注点、阻力点，以及满足关注点、避免阻力点所需的功能、非功能需求也是一个重要...` supplies neighboring source evidence: "识别出关键干系人只是第一步，选择合适的代表进行调研，分析他们的关注点、阻力点，以及满足关注点、避免阻力点所需的功能、非功能需求也是一个重要任务。 干系人分析任务执行指引如图5-1所示。"[^anchor:5-干系人分析-evidence::effective-requirements-0032].

`很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...` supplies neighboring source evidence: "很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需求”这个概念，是执行好该任务的关键。 干系人负需求 案例分析 很多年前，我参与了一些电子政务系统的开发，在一次省、市、县三级的“效能监管系统”项目中遇到了一件有趣的事情。 这个项目首先在省厅进行了需求调研，调研告一段落后，省厅领导让我们到A市——他们最有代表性的一个地级市进行深入调研。 去的那天，路上"[^anchor:5-干系人分析-evidence::effective-requirements-0033].

These anchors justify an llm_agentic candidate only where the user needs interpretation, conflict arbitration, or missing-context judgment; deterministic execution remains in workflow_candidates/.

Scenario-family anchor coverage: `should_trigger` `resistance-changes-scope` -> `5-干系人分析-principle::0012`, `5-干系人分析-evidence::effective-requirements-0032` (这里需要判断关注点和阻力点的权重，不是填写干系人表。); `should_trigger` `graph-inferred-link-derives_case_signal::principle::0012->case::effective-requirements-0033` -> `derives_case_signal::principle::0012->case::effective-requirements-0033` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `stakeholder-inventory-only` -> `5-干系人分析-principle::0012`, `5-干系人分析-evidence::effective-requirements-0032` (这是确定性识别流程，应保留在 workflow_candidates/。); `edge_case` `missing-real-user` -> `5-干系人分析-principle::0012`, `5-干系人分析-evidence::effective-requirements-0032` (需要判断缺失干系人是否足以阻断结论。); `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0034` -> `counter-example::effective-requirements-0034` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `single-stakeholder-no-conflict` -> `5-干系人分析-principle::0012`, `5-干系人分析-evidence::effective-requirements-0032` (不应为无冲突场景制造 agentic 判断。).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0012->case::effective-requirements-0033` (`5 干系人分析` -> `很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...`, source_location `sources/有效需求分析（第2版）.md:1242-1311`), `derives_case_signal::principle::0012->case::effective-requirements-0034` (`5 干系人分析` -> `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`, source_location `sources/有效需求分析（第2版）.md:1314-1375`), `derives_counter_example_signal::principle::0012->counter-example::effective-requirements-0034` (`5 干系人分析` -> `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`, source_location `sources/有效需求分析（第2版）.md:1314-1375`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0034` at source_location `sources/有效需求分析（第2版）.md:1314-1375` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0010`/3 目标/愿景分析 Cluster, `community::principle::0012`/5 干系人分析 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by: []
complements: []
contradicts: []
```

## Usage Summary
Current trace attachments: 1.

- 当关注点和阻力点冲突时，输出关键干系人、取舍理由和忽略风险。
- 如果只是补干系人列表，应路由到 workflow_candidates/4-干系人识别 或 5-干系人分析。
- 必须显式检查遗漏干系人和被低估阻力，不能只给沟通建议。
- 当关键干系人身份不确定时，先 ask_for_missing_stakeholder。

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0012->case::effective-requirements-0033` (`5 干系人分析` -> `很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...`, source_location `sources/有效需求分析（第2版）.md:1242-1311`), `derives_case_signal::principle::0012->case::effective-requirements-0034` (`5 干系人分析` -> `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`, source_location `sources/有效需求分析（第2版）.md:1314-1375`), `derives_counter_example_signal::principle::0012->counter-example::effective-requirements-0034` (`5 干系人分析` -> `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`, source_location `sources/有效需求分析（第2版）.md:1314-1375`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0034` at source_location `sources/有效需求分析（第2版）.md:1314-1375` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0010`/3 目标/愿景分析 Cluster, `community::principle::0012`/5 干系人分析 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `resistance-changes-scope`; 业务方关注效率，审计或运营方担心风险，需求范围需要在冲突中取舍。; signals: 一方要快 / 另一方担心风险 / 到底听谁的; boundary: 这里需要判断关注点和阻力点的权重，不是填写干系人表。; next: 输出 prioritize_resistance/prioritize_attention、critical_stakeholders、risk_if_ignored。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0012->case::effective-requirements-0033`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0012->case::effective-requirements-0033` expands trigger language only when a live decision links `5 干系人分析` and `很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...`.; signals: 5 干系人分析 / 很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需... / 很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需求”这个概念，是...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:1242-1311` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0012->case::effective-requirements-0034`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0012->case::effective-requirements-0034` expands trigger language only when a live decision links `5 干系人分析` and `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`.; signals: 5 干系人分析 / 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)... / 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)按KPI分解：K...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:1314-1375` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0012->counter-example::effective-requirements-0034`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0012->counter-example::effective-requirements-0034` expands trigger language only when a live decision links `5 干系人分析` and `1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...`.; signals: 5 干系人分析 / 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)... / 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)按KPI分解：K...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:1314-1375` before expanding the trigger.
- `should_not_trigger` `stakeholder-inventory-only`; 用户只要求列出项目干系人和基本职责。; signals: 帮我列干系人 / 整理角色列表; boundary: 这是确定性识别流程，应保留在 workflow_candidates/。
- `edge_case` `missing-real-user`; 发起人明确，但真实使用者或受影响群体没有被访谈。; signals: 领导提的 / 一线没人参与 / 不知道谁会反对; boundary: 需要判断缺失干系人是否足以阻断结论。; next: 输出 ask_for_missing_stakeholder 和最小补访谈列表。
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0034`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0034` is a boundary probe, not a permission to fire broadly.; signals: 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)... / 1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)按KPI分解：K...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:1314-1375`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `single-stakeholder-no-conflict`; 只有一个明确使用者且无冲突，只需继续执行固定分析模板。; signals: 只有一个使用部门 / 没有争议; boundary: 不应为无冲突场景制造 agentic 判断。

Representative cases:
- `traces/canonical/stakeholder-resistance-tradeoff-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- If `stakeholder_list_is_only_being_filled` remains true, defer the skill instead of firing.
- If `critical_stakeholder_identity_uncertain` is observed, treat the evidence as conflicting.

场景族覆盖：`should_trigger`=4，`should_not_trigger`=1，`edge_case`=2，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Replace generated smoke cases with real project review logs.
- Verify the skill against mixed stakeholder and scope-trimming cases before broad publication.


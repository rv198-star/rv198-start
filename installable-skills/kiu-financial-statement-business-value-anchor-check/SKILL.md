---
name: kiu-financial-statement-business-value-anchor-check
description: Use this KiU-generated action skill from Financial Statement Analysis when the task matches `business-value-anchor-check`.
---

# Business Value Anchor Check

## Identity
```yaml
skill_id: business-value-anchor-check
title: Business Value Anchor Check
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - business_value_anchor_check_decision_required
  - business_value_anchor_check_evidence_grounded
  exclusions:
  - concept_query_only
  - business_value_anchor_check_outside_operating_boundary
intake:
  required:
  - name: scenario
    type: structured
    description: Scenario summary that may require this principle or skill.
  - name: decision_goal
    type: string
    description: The concrete decision, tradeoff, or next action under review.
  - name: decision_scope
    type: string
    description: What part of the decision is in scope, and what must stay outside
      the boundary.
  - name: current_constraints
    type: list[string]
    description: Operational constraints, missing context, or boundary conditions
      that could block firing.
  - name: disconfirming_evidence
    type: list[string]
    description: Evidence that would make this skill unsafe to apply or require deferral.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[apply|defer|do_not_apply]
      next_action: string
      evidence_to_check: list[string]
      decline_reason: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - disconfirming_evidence_present
  - business_value_anchor_check_evidence_conflict
  do_not_fire_when:
  - scenario_missing_decision_context
  - business_value_anchor_check_boundary_unclear
```

## Rationale
`Business Value Anchor Check` is distilled from the source excerpt "## E16.13. 根据经营性收益增长预测进行估值：耐克公司（中等）"[^anchor:business-value-anchor-check-principle::1098]. The draft treats this as a decision-facing principle rather than a thematic summary: the contract asks for a concrete scenario, a clear decision goal, and explicit constraints so the skill can judge whether the principle should actively fire, be deferred, or stay out of scope. `在本章的阅读材料 16-4 中，使用剩余经营性收益模型对耐克公司的股份进行了估值。接下来，请完成下列要求： a. 对阅读材料 16-4 中...` adds operational context through "在本章的阅读材料 16-4 中，使用剩余经营性收益模型对耐克公司的股份进行了估值。接下来，请完成下列要求： a. 对阅读材料 16-4 中的预计数据进行修正，计算预计超常增长的经营性收益为多少，然后再对耐克公司的股份进行估值。 b. 同时考虑短期和长期的增长率情况，应用简单估值模型 [式（15-5）] 对耐克公司的股份进行估值，可参考阅读材料 15-4 中的内容。"[^anchor:business-value-anchor-check-evidence::financial-statement-1202]. `完全信息预测：耐克公司` adds operational context through "# 完全信息预测：耐克公司"[^anchor:business-value-anchor-check-framework::1054]. The boundary remains narrow by design: if `disconfirming_evidence_present` or `scenario_missing_decision_context` is true, the skill should not over-claim.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `如果某家企业的权益市价已经低于了其净金融性资产的价值，就意味着市场认为这家企业的经营价值已经成为负数。所以，在正常情况下，企业的权益价值至...` — 如果某家企业的权益市价已经低于了其净金融性资产的价值，就意味着市场认为这家企业的经营价值已经成为负数。所以，在正常情况下，企业的权益价值至少是大于等于其净金融性资产价值的，于是，可将企业的货币资金水平作为估值的底限（即不考虑任何经营价值的条件下的企业价值）。举例来说，戴尔公司的股票在2011年2月的交易价格为每股14.25美元，在它的战略资产负债表中，净金融性资产为90.32亿美元，流通在外的股份数量为19.18亿股，因此，该公司的每股[^anchor:business-value-anchor-check-evidence::financial-statement-0668]
- mechanism observed: `如果某家企业的权益市价已经低于了其净金融性资产的价值，就意味着市场认为这家企业的经营价值已经成为负数。所以，在正常情况下，企业的权益价值至...` contains mechanism-density `0.625`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Business Value Anchor Check` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `business_value_anchor_check_decision_required`
- anti-misuse boundary: `scenario_missing_decision_context`

### Downstream Use Check
This skill must separate value signal from value conclusion: state the claim under test, the source-backed evidence supporting it, the competing explanation or missing proof, and the next verification step before action.

Minimum Pressure Pass (evidence pressure): Ask exactly where the value claim exceeds available evidence; if the proof is missing, output the verification step or a safer provisional action instead of a value conclusion. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Business Value Anchor Check` is primarily anchored to "## E16.13. 根据经营性收益增长预测进行估值：耐克公司（中等）"[^anchor:business-value-anchor-check-principle::1098].

`在本章的阅读材料 16-4 中，使用剩余经营性收益模型对耐克公司的股份进行了估值。接下来，请完成下列要求： a. 对阅读材料 16-4 中...` preserves neighboring evidence: "在本章的阅读材料 16-4 中，使用剩余经营性收益模型对耐克公司的股份进行了估值。接下来，请完成下列要求： a. 对阅读材料 16-4 中的预计数据进行修正，计算预计超常增长的经营性收益为多少，然后再对耐克公司的股份进行估值。 b. 同时考虑短期和长期的增长率情况，应用简单估值模型 [式（15-5）] 对耐克公司的股份进行估值，可参考阅读材料 15-4 中的内容。"[^anchor:business-value-anchor-check-evidence::financial-statement-1202].

`完全信息预测：耐克公司` preserves neighboring evidence: "# 完全信息预测：耐克公司"[^anchor:business-value-anchor-check-framework::1054].

These excerpts remain bound to both `anchors.yaml` and the source-backed graph snapshot.

Scenario-family anchor coverage: `should_trigger` `live-decision-window` -> `business-value-anchor-check-principle::1098`, `business-value-anchor-check-evidence::financial-statement-1202` (The scenario already contains a concrete decision boundary.); `should_trigger` `graph-inferred-link-derives_case_signal::principle::0981->case::financial-statement-1070` -> `derives_case_signal::principle::0981->case::financial-statement-1070` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `concept-query-only` -> `business-value-anchor-check-principle::1098`, `business-value-anchor-check-evidence::financial-statement-1202` (The user is learning a concept, not applying a decision principle.); `edge_case` `partial-fit-boundary` -> `business-value-anchor-check-principle::1098`, `business-value-anchor-check-evidence::financial-statement-1202` (The decision pattern overlaps, but important context is still missing.); `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-1038` -> `counter-example::financial-statement-1038` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `missing-decision-context` -> `business-value-anchor-check-principle::1098`, `business-value-anchor-check-evidence::financial-statement-1202` (The principle should not fire without a stable decision boundary.).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0981->case::financial-statement-1070` (`M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` -> `丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、...`, source_location `sources/财务报表分析_Markdown版.md:13073-13083`), `derives_case_signal::principle::0981->case::financial-statement-1071` (`M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` -> `| 0 | 1 | 2 | 3 | 4 | |:--------|:------|:------|:------|:------| | |...`, source_location `sources/财务报表分析_Markdown版.md:13085-13103`), `derives_counter_example_signal::principle::0948->counter-example::financial-statement-1038` (`14.6 企业估值乘数` -> `在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 ...`, source_location `sources/财务报表分析_Markdown版.md:12687-12687`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::financial-statement-1038` at source_location `sources/财务报表分析_Markdown版.md:12687-12687` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0084`/思考题 Cluster, `community::principle::0087`/E1.1. 计算企业价值（简单） Cluster; use this for related-skill handoff, not as independent evidence.

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

- Use `Business Value Anchor Check` when the scenario materially resembles the decision pattern in `E16.13. 根据经营性收益增长预测进行估值：耐克公司（中等）`.
- Do not fire on concept-only questions; confirm there is a live decision with in-scope boundary context.
- Verify the scenario already includes enough concrete context and disconfirming evidence to test the boundary before firing.

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0981->case::financial-statement-1070` (`M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` -> `丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、...`, source_location `sources/财务报表分析_Markdown版.md:13073-13083`), `derives_case_signal::principle::0981->case::financial-statement-1071` (`M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` -> `| 0 | 1 | 2 | 3 | 4 | |:--------|:------|:------|:------|:------| | |...`, source_location `sources/财务报表分析_Markdown版.md:13085-13103`), `derives_counter_example_signal::principle::0948->counter-example::financial-statement-1038` (`14.6 企业估值乘数` -> `在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 ...`, source_location `sources/财务报表分析_Markdown版.md:12687-12687`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::financial-statement-1038` at source_location `sources/财务报表分析_Markdown版.md:12687-12687` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0084`/思考题 Cluster, `community::principle::0087`/E1.1. 计算企业价值（简单） Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `live-decision-window`; Business Value Anchor Check fires when the scenario contains a live decision this principle can materially improve.; signals: 需要做决定 / 如何判断 / 下一步怎么做; boundary: The scenario already contains a concrete decision boundary.; next: 输出与该原则相匹配的具体 next action。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0981->case::financial-statement-1070`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0981->case::financial-statement-1070` expands trigger language only when a live decision links `M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` and `丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、...`.; signals: M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司 / 丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、... / 丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、丘博国际、丘博保...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:13073-13083` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0981->case::financial-statement-1071`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0981->case::financial-statement-1071` expands trigger language only when a live decision links `M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` and `| 0 | 1 | 2 | 3 | 4 | |:--------|:------|:------|:------|:------| | |...`.; signals: M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司 / | 0 | 1 | 2 | 3 | 4 | |:--------|:------|:------|:------|:------| | |... / | 0 | 1 | 2 | 3 | 4 | |:--------|:------|:------|:------|:------| | | 2010年 |...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:13085-13103` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0948->counter-example::financial-statement-1038`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0948->counter-example::financial-statement-1038` expands trigger language only when a live decision links `14.6 企业估值乘数` and `在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 ...`.; signals: 14.6 企业估值乘数 / 在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 ... / 在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 中，你可能还注意...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:12687-12687` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0092->term::hewlett-packard`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0092->term::hewlett-packard` expands trigger language only when a live decision links `E1.5. 企业的市场价值：通用磨坊公司和惠普公司（中等）` and `Hewlett-Packard`.; signals: E1.5. 企业的市场价值：通用磨坊公司和惠普公司（中等） / Hewlett-Packard / a. 通用磨坊公司（General Mills, Inc.）是一家大型包装食品制造商，在截至2011年5月29日的年度报告中，它报告了下列信息（金额单位：...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:1480-1496` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0343->term::john-hancock-mutual-life-insurance`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0343->term::john-hancock-mutual-life-insurance` expands trigger language only when a live decision links `保险公司的股份化：这些企业的价值大于它们的账面价值吗` and `John Hancock Mutual Life insurance`.; signals: 保险公司的股份化：这些企业的价值大于它们的账面价值吗 / John Hancock Mutual Life insurance / 包括恒康人寿保险公司（John Hancock Mutual Life insurance）和大都会人寿保险公司（Metropolitan Life In...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:4612-4628` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0343->term::metropolitan-life-insurance`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0343->term::metropolitan-life-insurance` expands trigger language only when a live decision links `保险公司的股份化：这些企业的价值大于它们的账面价值吗` and `Metropolitan Life Insurance`.; signals: 保险公司的股份化：这些企业的价值大于它们的账面价值吗 / Metropolitan Life Insurance / 包括恒康人寿保险公司（John Hancock Mutual Life insurance）和大都会人寿保险公司（Metropolitan Life In...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:4612-4628` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0981->term::hurricane-katrina`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0981->term::hurricane-katrina` expands trigger language only when a live decision links `M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司` and `Hurricane Katrina`.; signals: M14.1 对一家财产保险公司的经营和投资进行估值：丘博公司 / Hurricane Katrina / 丘博公司是一家财险控股公司，它的分支机构遍布美国、加拿大、欧洲和部分拉丁美洲与亚洲国家，旗下拥有联邦保险、思危保险、太平洋保险、大北保险、丘博国际、丘博保...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:13073-13083` before expanding the trigger.
- `should_not_trigger` `concept-query-only`; Do not fire on concept-only questions without a live decision.; signals: 是什么概念 / 怎么定义 / 解释一下; boundary: The user is learning a concept, not applying a decision principle.
- `edge_case` `partial-fit-boundary`; Use edge handling when the principle partially fits but the boundary is still ambiguous.; signals: 有点像 / 不确定是否适用; boundary: The decision pattern overlaps, but important context is still missing.; next: 先补关键上下文，再决定 full_apply / partial_review / defer。
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-1038`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-1038` is a boundary probe, not a permission to fire broadly.; signals: 在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 ... / 在表 14-5 金融杠杆影响的例题中，你也许已经发现，随着杠杆程度的增加，市净率也增大了，从 1.2 变为了 1.33。而在表 14-6 中，你可能还注意...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:12687-12687`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `missing-decision-context`; Refuse when the scenario lacks enough decision context or disconfirming evidence.; signals: 信息还不够 / 只是先了解一下; boundary: The principle should not fire without a stable decision boundary.

Representative cases:
- `traces/canonical/business-value-anchor-check-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- If `scenario_missing_decision_context` remains true, defer the skill instead of firing.
- If `disconfirming_evidence_present` is observed, treat the evidence as conflicting.

场景族覆盖：`should_trigger`=8，`should_not_trigger`=1，`edge_case`=2，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Confirm whether the current trigger symbols are specific enough for production use.
- Replace smoke evaluation with real domain cases before publication.


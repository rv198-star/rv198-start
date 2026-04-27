---
name: kiu-effective-requirements-solution-to-problem-reframing
description: Use this KiU-generated action skill from Effective Requirements Analysis when the task matches `solution-to-problem-reframing`.
---

# Solution To Problem Reframing

## Identity
```yaml
skill_id: solution-to-problem-reframing
title: Solution To Problem Reframing
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - solution_level_request_with_unclear_problem
  - stakeholder_requests_feature_but_business_impact_unknown
  - implementation_cost_debate_before_problem_recovery
  exclusions:
  - workflow_execution_request_only
  - problem_already_validated_and_solution_selected
  - concept_query_only
intake:
  required:
  - name: proposed_solution
    type: string
    description: 用户或客户已经提出的功能、页面、报表或实现方案。
  - name: requester_and_user
    type: structured
    description: 区分需求提出者、真实使用者、受影响者是否一致。
  - name: business_impact_if_absent
    type: list[string]
    description: 如果不做该方案，业务问题、风险或机会损失是什么。
  - name: current_workaround
    type: string
    description: 当前临时解决方式及其代价。
  - name: disconfirming_evidence
    type: list[string]
    description: 能证明该方案只是表层表达、问题尚未澄清或价值不足的证据。
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[reframe_to_problem|accept_solution_with_constraints|defer]
      problem_level_need: string
      solution_risk: list[string]
      evidence_to_check: list[string]
      next_question: string
      decline_reason: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - problem_level_need_cannot_be_recovered
  - requester_and_real_user_conflict_unresolved
  do_not_fire_when:
  - workflow_execution_request_only
  - problem_already_validated_and_solution_selected
```

## Rationale
`Solution To Problem Reframing` is anchored in "### 2 日常需求分析"[^anchor:2-日常需求分析-principle::0008]. `在信息化应用相当普及的当下，根据客户、市场、业务部门的需求反馈，针对已发布的产品、已投产的系统进行持续优化，是最典型的需求分析场景。因此，...` adds source context through "在信息化应用相当普及的当下，根据客户、市场、业务部门的需求反馈，针对已发布的产品、已投产的系统进行持续优化，是最典型的需求分析场景。因此，本章就针对这一工作任务进行详细讲解，同时帮助读者建立基本的需求分析观。 日常需求分析任务执行指引如图2-1所示。 ![](https://res.weread.qq.com/wrepub/CB_3300091715_5XUAMg3fw3fv6L83H93Hr2yp5Lc26ecd.jpg) 当我们收到"[^anchor:2-日常需求分析-evidence::effective-requirements-0012]. `要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...` adds source context through "要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业务驱动的需求思想，也就是避免简单地从技术视角展开、细化“方案级需求”，而应该先从用户视角、业务视角探究背后的“问题级需求”，然后找到能够解决问题，并且开发成本更合适的解决方案。 案例分析 小王是一名实战经验还很少的需求分析师，在一次酒店管理系统的建设项目中，听到酒店前台人员提出一条需求：请在酒店入住界"[^anchor:2-日常需求分析-evidence::effective-requirements-0013]. This candidate is intentionally not a workflow wrapper. It fires when the input requires reconstructing the real problem behind a proposed solution, judging whether the requester's wording is reliable, and deciding whether to reframe, accept with constraints, or defer. The underlying chapter still provides deterministic restore/complement/evaluate workflows, but this skill handles the judgment boundary before those workflows are chosen. The output must name the evidence it checked, the boundary reason, and a concrete next action; otherwise it should defer or route back to workflow_candidates/.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多...` — 对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多的建议时，会提升客户的期望值。 针对这样的两难问题，我个人的经验是“只挖掘问题，不挖掘方案”。因为对于问题级的探讨，客户是理性的；而对于方案级的探讨，客户是感性的。但无论怎么做，这些工作都需要投入更多的精力和时间，因此在实战中要有所取舍。 1.提高广度——同类问题横推法 由于很多需求提出者经常会进入“[^anchor:solution-to-problem-reframing-case::effective-requirements-0017]
- mechanism observed: `对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多...` contains mechanism-density `0.625`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Solution To Problem Reframing` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `solution_level_request_with_unclear_problem`
- anti-misuse boundary: `workflow_execution_request_only`

### Downstream Use Check
This skill must make `Solution To Problem Reframing` usable by turning the reframed problem into a decision, owner, and next information request.

Minimum Pressure Pass (downstream pressure): Ask what the downstream actor would still need to invent after the reframing; if ownership, success criteria, or first action is missing, return the missing handoff rather than a polished reframe. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Solution To Problem Reframing` is grounded in "### 2 日常需求分析"[^anchor:2-日常需求分析-principle::0008].

`在信息化应用相当普及的当下，根据客户、市场、业务部门的需求反馈，针对已发布的产品、已投产的系统进行持续优化，是最典型的需求分析场景。因此，...` supplies neighboring source evidence: "在信息化应用相当普及的当下，根据客户、市场、业务部门的需求反馈，针对已发布的产品、已投产的系统进行持续优化，是最典型的需求分析场景。因此，本章就针对这一工作任务进行详细讲解，同时帮助读者建立基本的需求分析观。 日常需求分析任务执行指引如图2-1所示。 ![](https://res.weread.qq.com/wrepub/CB_3300091715_5XUAMg3fw3fv6L83H93Hr2yp5Lc26ecd.jpg) 当我们收到"[^anchor:2-日常需求分析-evidence::effective-requirements-0012].

`要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...` supplies neighboring source evidence: "要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业务驱动的需求思想，也就是避免简单地从技术视角展开、细化“方案级需求”，而应该先从用户视角、业务视角探究背后的“问题级需求”，然后找到能够解决问题，并且开发成本更合适的解决方案。 案例分析 小王是一名实战经验还很少的需求分析师，在一次酒店管理系统的建设项目中，听到酒店前台人员提出一条需求：请在酒店入住界"[^anchor:2-日常需求分析-evidence::effective-requirements-0013].

These anchors justify an llm_agentic candidate only where the user needs interpretation, conflict arbitration, or missing-context judgment; deterministic execution remains in workflow_candidates/.

Scenario-family anchor coverage: `should_trigger` `feature-request-before-problem` -> `2-日常需求分析-principle::0008`, `2-日常需求分析-evidence::effective-requirements-0012` (这需要判断方案级表达背后的问题级需求，不能只执行固定清单。); `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0013` -> `derives_case_signal::principle::0008->case::effective-requirements-0013` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `routine-template-fill` -> `2-日常需求分析-principle::0008`, `2-日常需求分析-evidence::effective-requirements-0012` (这是高 workflow certainty + 高 context certainty，应进入 workflow_candidates/。); `edge_case` `requester-not-real-user` -> `2-日常需求分析-principle::0008`, `2-日常需求分析-evidence::effective-requirements-0012` (需要 agentic 判断并补上下文，而不是直接选择流程。); `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0013` -> `counter-example::effective-requirements-0013` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `solution-already-validated` -> `2-日常需求分析-principle::0008`, `2-日常需求分析-evidence::effective-requirements-0012` (不应把确定性执行伪装成厚 skill。).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0008->case::effective-requirements-0013` (`2 日常需求分析` -> `要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...`, source_location `sources/有效需求分析（第2版）.md:262-357`), `derives_case_signal::principle::0008->case::effective-requirements-0015` (`2 日常需求分析` -> `在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽...`, source_location `sources/有效需求分析（第2版）.md:380-407`), `derives_case_signal::principle::0008->case::effective-requirements-0016` (`2 日常需求分析` -> `这段对话是否能够让你对“问题级”需求有更清晰的理解呢？是否让你看到了更清晰的需求呢？在这里我们澄清了问题、了解了当前遇到该问题时的临时解决...`, source_location `sources/有效需求分析（第2版）.md:410-439`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0013` at source_location `sources/有效需求分析（第2版）.md:262-357`, `counter-example::effective-requirements-0015` at source_location `sources/有效需求分析（第2版）.md:380-407` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0007`/1 软件需求全景图 Cluster, `community::principle::0008`/2 日常需求分析 Cluster; use this for related-skill handoff, not as independent evidence.

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

- 当用户拿着一个明确方案来问要不要做时，先恢复问题级需求，而不是直接细化 How。
- 输出必须区分 proposed_solution、problem_level_need、solution_risk 和 next_question。
- 如果问题已验证且只是要执行固定模板，应路由到 workflow_candidates/2-日常需求分析，而不是触发本 skill。
- 如果真实用户与需求提出者不一致，必须显式标出需要补访谈或补证据。

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0008->case::effective-requirements-0013` (`2 日常需求分析` -> `要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...`, source_location `sources/有效需求分析（第2版）.md:262-357`), `derives_case_signal::principle::0008->case::effective-requirements-0015` (`2 日常需求分析` -> `在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽...`, source_location `sources/有效需求分析（第2版）.md:380-407`), `derives_case_signal::principle::0008->case::effective-requirements-0016` (`2 日常需求分析` -> `这段对话是否能够让你对“问题级”需求有更清晰的理解呢？是否让你看到了更清晰的需求呢？在这里我们澄清了问题、了解了当前遇到该问题时的临时解决...`, source_location `sources/有效需求分析（第2版）.md:410-439`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0013` at source_location `sources/有效需求分析（第2版）.md:262-357`, `counter-example::effective-requirements-0015` at source_location `sources/有效需求分析（第2版）.md:380-407` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0007`/1 软件需求全景图 Cluster, `community::principle::0008`/2 日常需求分析 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `feature-request-before-problem`; 客户要求加一个具体功能，但业务影响、真实使用者和替代方案都不清楚。; signals: 客户说必须加这个按钮 / 先别问为什么，赶紧实现 / 开发说成本很高; boundary: 这需要判断方案级表达背后的问题级需求，不能只执行固定清单。; next: 输出 reframe_to_problem、problem_level_need、solution_risk、next_question。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0013`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0013` expands trigger language only when a live decision links `2 日常需求分析` and `要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...`.; signals: 2 日常需求分析 / 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业... / 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业务驱动的需求思想...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:262-357` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0015`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0015` expands trigger language only when a live decision links `2 日常需求分析` and `在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽...`.; signals: 2 日常需求分析 / 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽... / 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽可能地收集需求使...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:380-407` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0016`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0016` expands trigger language only when a live decision links `2 日常需求分析` and `这段对话是否能够让你对“问题级”需求有更清晰的理解呢？是否让你看到了更清晰的需求呢？在这里我们澄清了问题、了解了当前遇到该问题时的临时解决...`.; signals: 2 日常需求分析 / 这段对话是否能够让你对“问题级”需求有更清晰的理解呢？是否让你看到了更清晰的需求呢？在这里我们澄清了问题、了解了当前遇到该问题时的临时解决... / 这段对话是否能够让你对“问题级”需求有更清晰的理解呢？是否让你看到了更清晰的需求呢？在这里我们澄清了问题、了解了当前遇到该问题时的临时解决方案（现状），并...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:410-439` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0017`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0017` expands trigger language only when a live decision links `2 日常需求分析` and `对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多...`.; signals: 2 日常需求分析 / 对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多... / 对于是否应该挖掘、补充需求，有人赞成，认为不考虑周全，客户迟早也会提出，后面开发更麻烦；有人反对，认为很容易产生需求蔓延，而且当你提出更多的建议时，会提升...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:442-465` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0018`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0018` expands trigger language only when a live decision links `2 日常需求分析` and `在这段对话中，我又得到了两个潜在的可能需要解决的问题：“找到一间不吵的房间”“找到不在楼道尽头的房间”，它们出现的频率更低，前者处理不好引...`.; signals: 2 日常需求分析 / 在这段对话中，我又得到了两个潜在的可能需要解决的问题：“找到一间不吵的房间”“找到不在楼道尽头的房间”，它们出现的频率更低，前者处理不好引... / 在这段对话中，我又得到了两个潜在的可能需要解决的问题：“找到一间不吵的房间”“找到不在楼道尽头的房间”，它们出现的频率更低，前者处理不好引发的后果更严重一...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:468-511` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0019`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0019` expands trigger language only when a live decision links `2 日常需求分析` and `评估需求的执行过程如图2-11所示，首先选择评估维度，然后针对每条需求进行逐一评估。 案例分析（续7） 通过前面的分析，我们完成了需求还原...`.; signals: 2 日常需求分析 / 评估需求的执行过程如图2-11所示，首先选择评估维度，然后针对每条需求进行逐一评估。 案例分析（续7） 通过前面的分析，我们完成了需求还原... / 评估需求的执行过程如图2-11所示，首先选择评估维度，然后针对每条需求进行逐一评估。 ![](https://res.weread.qq.com/wrep...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:514-545` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0008->case::effective-requirements-0020`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0008->case::effective-requirements-0020` expands trigger language only when a live decision links `2 日常需求分析` and `在实践中，针对每个变更/优化型需求（也称为日常需求），可以根据需要用“变更/优化型需求分析模板”整理出分析结果。 针对变更/优化型需求分析...`.; signals: 2 日常需求分析 / 在实践中，针对每个变更/优化型需求（也称为日常需求），可以根据需要用“变更/优化型需求分析模板”整理出分析结果。 针对变更/优化型需求分析... / 在实践中，针对每个变更/优化型需求（也称为日常需求），可以根据需要用“变更/优化型需求分析模板”整理出分析结果。 针对变更/优化型需求分析，有些公司在实践...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:548-571` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0008->counter-example::effective-requirements-0013`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0008->counter-example::effective-requirements-0013` expands trigger language only when a live decision links `2 日常需求分析` and `要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业...`.; signals: 2 日常需求分析 / 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业... / 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业务驱动的需求思想...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:262-357` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0008->counter-example::effective-requirements-0015`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0008->counter-example::effective-requirements-0015` expands trigger language only when a live decision links `2 日常需求分析` and `在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽...`.; signals: 2 日常需求分析 / 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽... / 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽可能地收集需求使...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:380-407` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0008->term::how`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0008->term::how` expands trigger language only when a live decision links `2 日常需求分析` and `How`.; signals: 2 日常需求分析 / How / 日常需求分析这一关键工作任务，可以分为还原需求、补充需求、评估需求三个步骤执行。 还原需求，核心要素有三个：Who（谁的需求）、Why（解决什么问题）、H...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:370-377` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0008->term::who-why`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0008->term::who-why` expands trigger language only when a live decision links `2 日常需求分析` and `Who+Why`.; signals: 2 日常需求分析 / Who+Why / 日常需求分析这一关键工作任务，可以分为还原需求、补充需求、评估需求三个步骤执行。 还原需求，核心要素有三个：Who（谁的需求）、Why（解决什么问题）、H...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:370-377` before expanding the trigger.
- `should_not_trigger` `routine-template-fill`; 用户已经确认 Who/Why/How，只要求按模板整理一条日常需求。; signals: 按变更需求模板整理 / 字段都齐了; boundary: 这是高 workflow certainty + 高 context certainty，应进入 workflow_candidates/。
- `edge_case` `requester-not-real-user`; 需求提出者和真实使用者不一致，需要判断当前方案是否误代表真实问题。; signals: 领导提的需求 / 一线用户没参与 / 不知道谁真正用; boundary: 需要 agentic 判断并补上下文，而不是直接选择流程。; next: 列出缺失访谈对象和最小验证问题。
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0013`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0013` is a boundary probe, not a permission to fire broadly.; signals: 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业... / 要做好日常需求分析工作，核心在于理解业务驱动思想，而该思想的基础就是理解需求的层次、透彻分析需求的价值评估维度。 在上一章中，我们提出了业务驱动的需求思想...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:262-357`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0015`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0015` is a boundary probe, not a permission to fire broadly.; signals: 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽... / 在明确是“谁”的需求时，不应仅把关注点放在需求提出者身上，还应该思考三个问题。 (1)需求提出者和需求使用者是否一致？如果不一致，则应该尽可能地收集需求使...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:380-407`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `solution-already-validated`; 业务问题、用户和约束都已验证，只剩下执行拆解。; signals: 目标和用户都确认了 / 只要拆任务; boundary: 不应把确定性执行伪装成厚 skill。

Representative cases:
- `traces/canonical/solution-to-problem-reframing-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- If `workflow_execution_request_only` remains true, defer the skill instead of firing.
- If `problem_level_need_cannot_be_recovered` is observed, treat the evidence as conflicting.

场景族覆盖：`should_trigger`=12，`should_not_trigger`=1，`edge_case`=3，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Replace generated smoke cases with real project review logs.
- Verify the skill against mixed stakeholder and scope-trimming cases before broad publication.


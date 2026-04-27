---
name: kiu-mao-anthology-principal-contradiction-focus
description: Use this KiU-generated action skill from Mao Anthology when the task matches `principal-contradiction-focus`.
---

# Principal Contradiction Focus

## Identity
```yaml
skill_id: principal-contradiction-focus
title: Principal Contradiction Focus
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - multiple_conflicts_compete_for_attention
  - strategy_requires_identifying_principal_contradiction
  - resources_are_spread_across_too_many_fronts
  exclusions:
  - pure_stance_commentary_without_user_decision
  - pure_summary_request
  - fact_lookup_request
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - mechanical_workflow_template_request
intake:
  required:
  - name: current_decision
    type: string
    description: The present decision, strategy, policy, or organizational judgment
      the user wants to improve.
  - name: source_pattern
    type: structured
    description: The source case, argument, or strategy pattern being considered for
      transfer.
  - name: transfer_conditions
    type: list[string]
    description: Conditions that must be true before the source pattern can be borrowed.
  - name: anti_conditions
    type: list[string]
    description: Conditions that block transfer, including single-case overreach and
      context-transfer abuse.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[focus_here|split_after_focus|ask_more_context|do_not_apply]
      principal_contradiction: string
      transfer_conditions: list[string]
      anti_conditions: list[string]
      abuse_check: enum[clear|single_case_overreach|context_transfer_abuse|insufficient_context]
      focused_action_program: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - transfer_conditions_missing
  - anti_conditions_dominate
  - context_transfer_abuse_detected
  do_not_fire_when:
  - pure_summary_request
  - pure_translation_request
  - fact_lookup_request
  - biography_intro_request
  - author_position_query
  - stance_commentary_without_user_decision
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - mechanical_workflow_template_request
```

## Rationale
`Principal Contradiction Focus` is a borrowed-value judgment skill anchored in "主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必然的结果，不是机会主义，就是盲动主义。至于党内的主观主义的批评，不要证据的乱说，或互相猜忌，往往酿成党内的无原则纠纷，破坏党的组织。 关于党内批评问题，还有一点要说及的，就是有些同志的批评不注意大的方面，只注意小的方面。他们不明白批评的主要任务，是指出政治上的错误和组织上的错误。至于个人缺点，如果不是"[^anchor:principal-contradiction-focus-situation-strategy::principal-contradiction-focus]. It should fire when the user faces multiple conflicts or fronts and must choose the main constraint before allocating action. The skill must not summarize, translate, introduce a person, answer a pure fact lookup, or comment on the author's stance as its main job; those remain source/retrieval tasks. Instead it maps the source pattern `principal-contradiction focus strategy` into a current decision only after checking transfer_conditions and anti_conditions. `主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必...` adds operational context through "主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必然的结果，不是机会主义，就是盲动主义。至于党内的主观主义的批评，不要证据的乱说，或互相猜忌，往往酿成党内的无原则纠纷，破坏党的组织。 关于党内批评问题，还有一点要说及的，就是有些同志的批评不注意大的方面，只注意小的方面。他们不明白批评的主要任务，是指出政治上的错误和组织上的错误。至于个人缺点，如果不是"[^anchor:principal-contradiction-focus-evidence::mao-0051]. `在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮...` adds operational context through "在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮有迅速到来的可能。因此他们不赞成争取江西的计划，而只赞成在福建、广东、江西之间的三个边界区域的流动游击，同时也没有在游击区域建立红色政权的深刻的观念，因此也就没有用这种红色政权的巩固和扩大去促进全国革命高潮的深刻的观念。他们似乎认为在距离革命高潮尚远的时期做这种建立政权的艰苦工作为徒劳，而希望用比较轻"[^anchor:principal-contradiction-focus-evidence::mao-0057]. The output must use `focus_here / split_after_focus / ask_more_context / do_not_apply` and include principal_contradiction, transfer_conditions, anti_conditions, abuse_check, and focused_action_program. It must explicitly detect `single_case_overreach` or `context_transfer_abuse` when the user tries to copy a book, historical case, competitor, large-company process, or past success without context fit.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮...` — 在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮有迅速到来的可能。因此他们不赞成争取江西的计划，而只赞成在福建、广东、江西之间的三个边界区域的流动游击，同时也没有在游击区域建立红色政权的深刻的观念，因此也就没有用这种红色政权的巩固和扩大去促进全国革命高潮的深刻的观念。他们似乎认为在距离革命高潮尚远的时期做这种建立政权的艰苦工作为徒劳，而希望用比较轻[^anchor:principal-contradiction-focus-evidence::mao-0057]
- mechanism observed: `在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮...` contains mechanism-density `0.5`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Principal Contradiction Focus` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `multiple_conflicts_compete_for_attention`
- anti-misuse boundary: `pure_summary_request`

### Downstream Use Check
This skill must make `Principal Contradiction Focus` decision-relevant by naming the main tension, the current action it changes, and the boundary that prevents treating every disagreement as the same problem.

Minimum Pressure Pass (alternative pressure): Test one competing problem frame before applying the skill; if a different tension better explains the situation, return that reframing or defer instead of forcing the original frame. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Principal Contradiction Focus` is grounded in borrowed-value evidence beginning with "主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必然的结果，不是机会主义，就是盲动主义。至于党内的主观主义的批评，不要证据的乱说，或互相猜忌，往往酿成党内的无原则纠纷，破坏党的组织。 关于党内批评问题，还有一点要说及的，就是有些同志的批评不注意大的方面，只注意小的方面。他们不明白批评的主要任务，是指出政治上的错误和组织上的错误。至于个人缺点，如果不是"[^anchor:principal-contradiction-focus-situation-strategy::principal-contradiction-focus].

`主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必...` preserves another source anchor for mechanism transfer: "主观主义，在某些党员中浓厚地存在，这对分析政治形势和指导工作，都非常不利。因为对于政治形势的主观主义的分析和对于工作的主观主义的指导，其必然的结果，不是机会主义，就是盲动主义。至于党内的主观主义的批评，不要证据的乱说，或互相猜忌，往往酿成党内的无原则纠纷，破坏党的组织。 关于党内批评问题，还有一点要说及的，就是有些同志的批评不注意大的方面，只注意小的方面。他们不明白批评的主要任务，是指出政治上的错误和组织上的错误。至于个人缺点，如果不是"[^anchor:principal-contradiction-focus-evidence::mao-0051].

`在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮...` preserves another source anchor for mechanism transfer: "在对于时局的估量和伴随而来的我们的行动问题上，我们党内有一部分同志还缺少正确的认识。他们虽然相信革命高潮不可避免地要到来，却不相信革命高潮有迅速到来的可能。因此他们不赞成争取江西的计划，而只赞成在福建、广东、江西之间的三个边界区域的流动游击，同时也没有在游击区域建立红色政权的深刻的观念，因此也就没有用这种红色政权的巩固和扩大去促进全国革命高潮的深刻的观念。他们似乎认为在距离革命高潮尚远的时期做这种建立政权的艰苦工作为徒劳，而希望用比较轻"[^anchor:principal-contradiction-focus-evidence::mao-0057].

The graph/source layer may extract summaries, chronology, facts, biography cues, positions, and source text broadly, but this skill consumes that evidence only for current decision transfer. Required transfer_conditions: multiple_conflicts_are_named, one_constraint_materially_controls_the_next_action, resource_allocation_changes_after_focus. Blocking anti_conditions: context_transfer_abuse, stance_commentary_without_user_decision, all_conflicts_are_independent_and_need_parallel_workflows. Pure summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision should not trigger the judgment skill.

Scenario-family anchor coverage: `should_trigger` `borrow-source-pattern-for-live-decision` -> `principal-contradiction-focus-situation-strategy::principal-contradiction-focus`, `principal-contradiction-focus-evidence::mao-0051` (There is a live current_decision and the user needs transferable judgment, not source explanation.); `should_not_trigger` `source-understanding-only` -> `principal-contradiction-focus-situation-strategy::principal-contradiction-focus`, `principal-contradiction-focus-evidence::mao-0051` (These are source/retrieval/QA tasks. The graph layer may extract them, but the judgment skill should not answer them as if they were transfer decisions.); `edge_case` `partial-transfer-with-material-differences` -> `principal-contradiction-focus-situation-strategy::principal-contradiction-focus`, `principal-contradiction-focus-evidence::mao-0051` (Borrow the mechanism only after naming both fit and non-fit conditions.); `refusal` `context-transfer-abuse` -> `principal-contradiction-focus-situation-strategy::principal-contradiction-focus`, `principal-contradiction-focus-evidence::mao-0051` (This is context_transfer_abuse: source material is being used as permission to bypass current-context judgment.); `refusal` `single-case-overreach` -> `principal-contradiction-focus-situation-strategy::principal-contradiction-focus`, `principal-contradiction-focus-evidence::mao-0051` (This is single_case_overreach: one case cannot carry a transferable decision without mechanism and counterexample checks.).

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

- Use this skill when the user faces multiple conflicts or fronts and must choose the main constraint before allocating action; the live current_decision must be explicit before the source pattern is transferred.
- Keep source extraction broad, but keep skill firing narrow: summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision belong outside this judgment skill.
- Before applying the pattern, list transfer_conditions and anti_conditions; if either side is missing, ask for more context or decline.
- Treat single_case_overreach and context_transfer_abuse as first-class abuse checks, especially when the user wants to copy a book, historical case, competitor, large-company process, or past success.
- Positive trigger signals include: 矛盾太多, 平均用力, 先抓哪个问题, 资源分散.
- Negative trigger signals include: 总结主要矛盾理论, 评价作者立场, 单纯政治评论, 没有当前行动选择.
- Output principal_contradiction, transfer_conditions, anti_conditions, abuse_check, and focused_action_program with a `focus_here / split_after_focus / ask_more_context / do_not_apply` verdict.

Scenario families:
- `should_trigger` `borrow-source-pattern-for-live-decision`; Principal Contradiction Focus fires when the user faces multiple conflicts or fronts and must choose the main constraint before allocating action.; signals: 矛盾太多 / 平均用力 / 先抓哪个问题; boundary: There is a live current_decision and the user needs transferable judgment, not source explanation.; next: Return principal_contradiction, transfer_conditions, anti_conditions, abuse_check, and focused_action_program with verdict focus_here / split_after_focus / ask_more_context / do_not_apply.
- `should_not_trigger` `source-understanding-only`; Do not fire when the user only asks for summary, translation, fact lookup, biography introduction, author-position query, or stance commentary without a current decision.; signals: 总结主要矛盾理论 / 评价作者立场 / 单纯政治评论; boundary: These are source/retrieval/QA tasks. The graph layer may extract them, but the judgment skill should not answer them as if they were transfer decisions.
- `edge_case` `partial-transfer-with-material-differences`; Use partial transfer when the source pattern is useful but actor incentives, constraints, time horizon, institution, or resource conditions differ materially.; signals: 有点像 / 但时代不同 / 能借鉴多少; boundary: Borrow the mechanism only after naming both fit and non-fit conditions.; next: Name fit conditions, non-fit conditions, and a reversible next action before applying the source pattern.
- `refusal` `context-transfer-abuse`; Refuse when the user wants to copy the book, historical case, competitor, big-company process, or past success without checking context fit.; signals: 书里这么做成功了 / 大公司都这么做 / 竞品这样做我们也照搬; boundary: This is context_transfer_abuse: source material is being used as permission to bypass current-context judgment.; next: Decline direct transfer and ask for current_decision, source_pattern, fit conditions, non-fit conditions, and disconfirming evidence.
- `refusal` `single-case-overreach`; Refuse when one attractive story or case is treated as enough proof for a current decision.; signals: 只凭这个案例 / 历史上有人成功 / 一个故事就说明; boundary: This is single_case_overreach: one case cannot carry a transferable decision without mechanism and counterexample checks.; next: Decline broad transfer; require at least mechanism mapping, current context fit, and counter-case search.

Representative cases:
- `traces/canonical/principal-contradiction-focus-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- Do not fire on pure summary, translation, fact lookup, biography introduction, author-position query, or stance commentary without a user decision; route those to source/retrieval paths.
- Do not let source admiration become context_transfer_abuse: copying a book, historical case, competitor, big-company process, or past success without current fit must be refused.
- Do not accept single_case_overreach; require mechanism mapping, transfer_conditions, anti_conditions, and counter-case or disconfirming evidence before transfer.

场景族覆盖：`should_trigger`=1，`should_not_trigger`=1，`edge_case`=1，`refusal`=2。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Replace smoke cases with external human-written borrowing scenarios for stronger usage evidence.
- Add more cross-domain counter-cases before using the pattern in high-stakes contexts.


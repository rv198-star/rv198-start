# Historical Analogy Transfer Gate

## Identity
```yaml
skill_id: historical-analogy-transfer-gate
title: Historical Analogy Transfer Gate
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - user_wants_to_transfer_case_or_history_to_current_decision
  - single_case_overreach_risk
  - analogy_needs_mechanism_not_story_mapping
  exclusions:
  - pure_history_query_or_translation
  - biography_intro_request
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
      verdict: enum[transfer|partial_transfer|do_not_transfer|ask_more_context]
      mechanism_mapping: string
      transfer_conditions: list[string]
      anti_conditions: list[string]
      abuse_check: enum[clear|single_case_overreach|context_transfer_abuse|insufficient_context]
      transfer_checked_next_action: string
      confidence: enum[low|medium|high]
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
`Historical Analogy Transfer Gate` is a borrowed-value judgment skill anchored in "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate]. It should fire when the user wants to borrow a historical, biographical, or case pattern for a current decision. The skill must not summarize, translate, introduce a person, answer a pure fact lookup, or comment on the author's stance as its main job; those remain source/retrieval tasks. Instead it maps the source pattern `historical case mechanism` into a current decision only after checking transfer_conditions and anti_conditions. `（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，...` adds operational context through "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-analogy-transfer-gate-evidence::mao-0001]. `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` adds operational context through "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:historical-analogy-transfer-gate-evidence::mao-0002]. The output must use `transfer / partial_transfer / do_not_transfer / ask_more_context` and include mechanism_mapping, transfer_conditions, anti_conditions, abuse_check, and transfer_checked_next_action. It must explicitly detect `single_case_overreach` or `context_transfer_abuse` when the user tries to copy a book, historical case, competitor, large-company process, or past success without context fit.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` — 谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和[^anchor:historical-analogy-transfer-gate-evidence::mao-0002]
- mechanism observed: `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` contains mechanism-density `0.5`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Historical Analogy Transfer Gate` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_wants_to_transfer_case_or_history_to_current_decision`
- anti-misuse boundary: `pure_summary_request`

## Evidence Summary
`Historical Analogy Transfer Gate` is grounded in borrowed-value evidence beginning with "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate].

`（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，...` preserves another source anchor for mechanism transfer: "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-analogy-transfer-gate-evidence::mao-0001].

`谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` preserves another source anchor for mechanism transfer: "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:historical-analogy-transfer-gate-evidence::mao-0002].

The graph/source layer may extract summaries, chronology, facts, biography cues, positions, and source text broadly, but this skill consumes that evidence only for current decision transfer. Required transfer_conditions: current_decision_is_explicit, actor_incentive_constraint_outcome_chain_matches, material_differences_are_named. Blocking anti_conditions: single_case_overreach, surface_similarity_only, pure_history_query_or_translation. Pure summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision should not trigger the judgment skill.

Scenario-family anchor coverage: `should_trigger` `borrow-source-pattern-for-live-decision` -> `historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate`, `historical-analogy-transfer-gate-evidence::mao-0001` (There is a live current_decision and the user needs transferable judgment, not source explanation.); `should_not_trigger` `source-understanding-only` -> `historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate`, `historical-analogy-transfer-gate-evidence::mao-0001` (These are source/retrieval/QA tasks. The graph layer may extract them, but the judgment skill should not answer them as if they were transfer decisions.); `edge_case` `partial-transfer-with-material-differences` -> `historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate`, `historical-analogy-transfer-gate-evidence::mao-0001` (Borrow the mechanism only after naming both fit and non-fit conditions.); `refusal` `context-transfer-abuse` -> `historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate`, `historical-analogy-transfer-gate-evidence::mao-0001` (This is context_transfer_abuse: source material is being used as permission to bypass current-context judgment.); `refusal` `single-case-overreach` -> `historical-analogy-transfer-gate-case-mechanism::historical-analogy-transfer-gate`, `historical-analogy-transfer-gate-evidence::mao-0001` (This is single_case_overreach: one case cannot carry a transferable decision without mechanism and counterexample checks.).

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

- Use this skill when the user wants to borrow a historical, biographical, or case pattern for a current decision; the live current_decision must be explicit before the source pattern is transferred.
- Keep source extraction broad, but keep skill firing narrow: summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision belong outside this judgment skill.
- Before applying the pattern, list transfer_conditions and anti_conditions; if either side is missing, ask for more context or decline.
- Treat single_case_overreach and context_transfer_abuse as first-class abuse checks, especially when the user wants to copy a book, historical case, competitor, large-company process, or past success.
- Positive trigger signals include: 历史案例能不能借鉴, 这个故事像不像我们的处境, 机制是否相同.
- Negative trigger signals include: 讲讲这段历史, 翻译一下, 人物介绍, 单个故事成功所以照做.
- Output mechanism_mapping, transfer_conditions, anti_conditions, abuse_check, and transfer_checked_next_action with a `transfer / partial_transfer / do_not_transfer / ask_more_context` verdict.

Scenario families:
- `should_trigger` `borrow-source-pattern-for-live-decision`; Historical Analogy Transfer Gate fires when the user wants to borrow a historical, biographical, or case pattern for a current decision.; signals: 历史案例能不能借鉴 / 这个故事像不像我们的处境 / 机制是否相同; boundary: There is a live current_decision and the user needs transferable judgment, not source explanation.; next: Return mechanism_mapping, transfer_conditions, anti_conditions, abuse_check, and transfer_checked_next_action with verdict transfer / partial_transfer / do_not_transfer / ask_more_context.
- `should_not_trigger` `source-understanding-only`; Do not fire when the user only asks for summary, translation, fact lookup, biography introduction, author-position query, or stance commentary without a current decision.; signals: 讲讲这段历史 / 翻译一下 / 人物介绍; boundary: These are source/retrieval/QA tasks. The graph layer may extract them, but the judgment skill should not answer them as if they were transfer decisions.
- `edge_case` `partial-transfer-with-material-differences`; Use partial transfer when the source pattern is useful but actor incentives, constraints, time horizon, institution, or resource conditions differ materially.; signals: 有点像 / 但时代不同 / 能借鉴多少; boundary: Borrow the mechanism only after naming both fit and non-fit conditions.; next: Name fit conditions, non-fit conditions, and a reversible next action before applying the source pattern.
- `refusal` `context-transfer-abuse`; Refuse when the user wants to copy the book, historical case, competitor, big-company process, or past success without checking context fit.; signals: 书里这么做成功了 / 大公司都这么做 / 竞品这样做我们也照搬; boundary: This is context_transfer_abuse: source material is being used as permission to bypass current-context judgment.; next: Decline direct transfer and ask for current_decision, source_pattern, fit conditions, non-fit conditions, and disconfirming evidence.
- `refusal` `single-case-overreach`; Refuse when one attractive story or case is treated as enough proof for a current decision.; signals: 只凭这个案例 / 历史上有人成功 / 一个故事就说明; boundary: This is single_case_overreach: one case cannot carry a transferable decision without mechanism and counterexample checks.; next: Decline broad transfer; require at least mechanism mapping, current context fit, and counter-case search.

Representative cases:
- `traces/canonical/historical-analogy-transfer-gate-source-smoke.yaml`

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


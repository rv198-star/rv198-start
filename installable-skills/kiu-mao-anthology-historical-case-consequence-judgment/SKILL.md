---
name: kiu-mao-anthology-historical-case-consequence-judgment
description: Use this KiU-generated action skill from Mao Anthology when the task matches `historical-case-consequence-judgment`.
---

# Historical Case Consequence Judgment

## Identity
```yaml
skill_id: historical-case-consequence-judgment
title: Historical Case Consequence Judgment
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - user_applying_historical_case_to_current_judgment
  - decision_depends_on_case_consequence_pattern
  - user_needs_tradeoff_from_multiple_historical_examples
  exclusions:
  - history_summary_only
  - fact_lookup_only
  - birth_year_or_biography_lookup_only
  - classical_text_translation_only
  - single_anecdote_without_decision
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - mechanical_workflow_template_request
intake:
  required:
  - name: current_decision
    type: string
    description: The live judgment, policy, strategy, or personal choice being compared
      against historical cases.
  - name: case_analogs
    type: list[structured]
    description: Historical episodes, actors, choices, and consequences that may illuminate
      the current decision.
  - name: relevant_differences
    type: list[string]
    description: Differences that could make the historical pattern unsafe to transfer.
  - name: decision_boundary
    type: string
    description: What this historical analogy can and cannot decide.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[apply_pattern|partial_apply|do_not_apply]
      case_pattern: string
      transfer_limits: list[string]
      decision_warning: string
      next_action: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - analogy_differences_dominate
  - current_decision_context_missing
  do_not_fire_when:
  - history_summary_only
  - fact_lookup_only
  - historical_fact_lookup_or_birth_year_question
  - classical_text_translation_to_modern_chinese
  - single_anecdote_without_decision
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - mechanical_workflow_template_request
```

## Rationale
`Historical Case Consequence Judgment` is anchored in multiple historical episodes, starting from "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment]. It should fire when the user is not merely asking what happened in history, but wants to use historical cases to judge a current choice, policy, strategy, or organizational tradeoff. The skill must extract a case-consequence pattern, then state where the analogy transfers and where it breaks. This is intentionally agentic: it requires comparing actors, incentives, constraints, timing, and consequences across cases before deciding whether the pattern applies. `（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，...` adds operational context through "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-case-consequence-judgment-evidence::mao-0001]. `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` adds operational context through "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:historical-case-consequence-judgment-evidence::mao-0002]. The output should be `apply_pattern / partial_apply / do_not_apply`, with a named case pattern, transfer limits, a decision warning, and a concrete next action. It must refuse pure history summaries, fact lookup, or single anecdote arguments that lack a live decision boundary.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` — 谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和[^anchor:historical-case-consequence-judgment-evidence::mao-0002]
- mechanism observed: `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` contains mechanism-density `0.5`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Historical Case Consequence Judgment` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_applying_historical_case_to_current_judgment`
- anti-misuse boundary: `history_summary_only`

### Downstream Use Check
This skill must make `Historical Case Consequence Judgment` safe to transfer by naming the source mechanism, the current mechanism, and the boundary that would make the analogy invalid.

Minimum Pressure Pass (evidence pressure): Check whether the shared mechanism is evidenced or merely story-similar; if only names, roles, or outcomes match, return do_not_apply or demand more context. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Historical Case Consequence Judgment` is anchored to historical case evidence beginning with "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment].

`（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，...` supplies an additional case or consequence anchor: "（一九二五年十二月一日） > 毛泽东此文是为反对当时党内存在着的两种倾向而写的。当时党内的第一种倾向，以陈独秀为代表，只注意同国民党合作，忘记了农民，这是右倾机会主义。第二种倾向，以张国焘为代表，只注意工人运动，同样忘记了农民，这是“左”倾机会主义。这两种机会主义都感觉自己力量不足，而不知道到何处去寻找力量，到何处去取得广大的同盟军。毛泽东指出中国无产阶级的最广大和最忠实的同盟军是农民，这样就解决了中国革命中的最主要的同盟军问题。毛泽东"[^anchor:historical-case-consequence-judgment-evidence::mao-0001].

`谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` supplies an additional case or consequence anchor: "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:historical-case-consequence-judgment-evidence::mao-0002].

These excerpts justify a judgment skill only when a user has a current decision and needs to compare historical case patterns, consequences, incentives, and transfer limits. They do not justify treating history as a deterministic recipe or using one anecdote as proof.

Scenario-family anchor coverage: `should_trigger` `historical-analogy-for-current-decision` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (There is a live decision and the user needs analogy transfer, not a history summary; the skill must compare mechanism, consequence, and transfer limit.); `should_trigger` `short-gain-long-cost-stress-test` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (The prompt is asking for a consequence chain, not a heroic-character judgment.); `should_not_trigger` `history-summary-only` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (史实查询、百科查询、翻译任务、编年、人物评价 and viewpoint summaries do not require decision-facing analogy judgment; 不应激活本 skill.); `edge_case` `suggestive-but-different-context` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (The analogy may help but cannot decide the case by itself.); `refusal` `single-anecdote-proof` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (One anecdote without transfer-limit analysis is unsafe evidence.); `refusal` `workflow-or-template-request` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::mao-0001` (Template generation is a workflow or writing task, not a historical-case consequence decision.).

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

- Use this skill when the user wants to apply historical cases to a live decision, not when they only ask for a summary of what happened.
- Ask for the current decision, candidate historical analogies, relevant differences, and the boundary of transfer before giving advice; if the user asks `司马迁是哪一年出生的？`, answer as a fact lookup outside this skill.
- Output a named case pattern, the consequences it highlights, transfer limits, and a concrete next action.
- Use `partial_apply` when the case pattern is suggestive but actor incentives, institutional context, or time horizon differ materially.
- Use `do_not_apply` when the user is cherry-picking one story, asking for fact lookup such as birth year/biography, asking to translate classical Chinese into modern Chinese, or ignoring decisive differences between the historical case and the current situation.

Scenario families:
- `should_trigger` `historical-analogy-for-current-decision`; The user wants to use one or more historical cases, such as 项羽和刘邦, to judge a current strategy, governance, investment, or 商业决策 where short-term strength may become long-term distrust.; signals: 这个历史案例能不能类比 / 项羽和刘邦 / 商业决策; boundary: There is a live decision and the user needs analogy transfer, not a history summary; the skill must compare mechanism, consequence, and transfer limit.; next: 列出 case_pattern、机制链、transfer_limits、decision_warning 和 next_action。
- `should_trigger` `short-gain-long-cost-stress-test`; The user sees a short-term gain but worries that the choice will create long-term retaliation, distrust, precedent, or second-order cost.; signals: 短期强势但长期失信 / 眼前收益很大 / 以后会反噬; boundary: The prompt is asking for a consequence chain, not a heroic-character judgment.; next: Build a choice -> constraint shift -> trust/retaliation/order-cost chain before recommending continue, pause, or narrow scope.
- `should_not_trigger` `history-summary-only`; Do not fire when the user only asks what happened, who someone was, when someone was born, or how to translate/explain a historical passage.; signals: 讲讲这段历史 / 这个人是谁 / 司马迁是哪一年出生; boundary: 史实查询、百科查询、翻译任务、编年、人物评价 and viewpoint summaries do not require decision-facing analogy judgment; 不应激活本 skill.
- `edge_case` `suggestive-but-different-context`; Use partial_apply when the historical pattern is suggestive but institutions, incentives, technology, or time horizon differ.; signals: 有点像 / 但时代不一样 / 能借鉴多少; boundary: The analogy may help but cannot decide the case by itself.; next: 先列出相似点、关键差异和不可迁移部分，再给 partial_apply。
- `refusal` `single-anecdote-proof`; Refuse when the user tries to prove a current decision only by citing one attractive historical anecdote.; signals: 只记得一个史记故事 / 历史上有人这么做成功了 / 所以我们也照做; boundary: One anecdote without transfer-limit analysis is unsafe evidence.; next: 要求补充 current_decision、case_analogs、relevant_differences；证据不足时输出 do_not_apply。
- `refusal` `workflow-or-template-request`; Refuse when the user asks for a meeting note, checklist, template, or mechanical workflow rather than historical consequence judgment.; signals: 会议纪要模板 / 流程清单 / 表格模板; boundary: Template generation is a workflow or writing task, not a historical-case consequence decision.; next: 不激活本 skill；route to workflow/template assistance if appropriate.

Representative cases:
- `traces/canonical/historical-case-consequence-judgment-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- If `history_summary_only` remains true, defer the skill instead of firing.
- If `analogy_differences_dominate` is observed, treat the evidence as conflicting.

场景族覆盖：`should_trigger`=2，`should_not_trigger`=1，`edge_case`=1，`refusal`=2。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Confirm whether the current trigger symbols are specific enough for production use.
- Replace smoke evaluation with real domain cases before publication.


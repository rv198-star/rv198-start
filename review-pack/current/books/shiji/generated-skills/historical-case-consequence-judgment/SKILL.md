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
`Historical Case Consequence Judgment` is anchored in multiple historical episodes, starting from "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment]. It should fire when the user is not merely asking what happened in history, but wants to use historical cases to judge a current choice, policy, strategy, or organizational tradeoff. The skill must extract a case-consequence pattern, then state where the analogy transfers and where it breaks. This is intentionally agentic: it requires comparing actors, incentives, constraints, timing, and consequences across cases before deciding whether the pattern applies. `昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失...` adds operational context through "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:historical-case-consequence-judgment-evidence::shiji-0001]. `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` adds operational context through "名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤"[^anchor:historical-case-consequence-judgment-evidence::shiji-0002]. The output should be `apply_pattern / partial_apply / do_not_apply`, with a named case pattern, transfer limits, a decision warning, and a concrete next action. It must refuse pure history summaries, fact lookup, or single anecdote arguments that lack a live decision boundary.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` — 名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤[^anchor:historical-case-consequence-judgment-evidence::shiji-0002]
- mechanism observed: `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` contains mechanism-density `0.875`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Historical Case Consequence Judgment` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_applying_historical_case_to_current_judgment`
- anti-misuse boundary: `history_summary_only`

## Evidence Summary
`Historical Case Consequence Judgment` is anchored to historical case evidence beginning with "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment].

`昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失...` supplies an additional case or consequence anchor: "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:historical-case-consequence-judgment-evidence::shiji-0001].

`名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` supplies an additional case or consequence anchor: "名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤"[^anchor:historical-case-consequence-judgment-evidence::shiji-0002].

These excerpts justify a judgment skill only when a user has a current decision and needs to compare historical case patterns, consequences, incentives, and transfer limits. They do not justify treating history as a deterministic recipe or using one anecdote as proof.

Scenario-family anchor coverage: `should_trigger` `historical-analogy-for-current-decision` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (There is a live decision and the user needs analogy transfer, not a history summary; the skill must compare mechanism, consequence, and transfer limit.); `should_trigger` `short-gain-long-cost-stress-test` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (The prompt is asking for a consequence chain, not a heroic-character judgment.); `should_not_trigger` `history-summary-only` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (史实查询、百科查询、翻译任务、编年、人物评价 and viewpoint summaries do not require decision-facing analogy judgment; 不应激活本 skill.); `edge_case` `suggestive-but-different-context` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (The analogy may help but cannot decide the case by itself.); `refusal` `single-anecdote-proof` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (One anecdote without transfer-limit analysis is unsafe evidence.); `refusal` `workflow-or-template-request` -> `historical-case-consequence-judgment-narrative-pattern::historical-case-consequence-judgment`, `historical-case-consequence-judgment-evidence::shiji-0001` (Template generation is a workflow or writing task, not a historical-case consequence decision.).

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


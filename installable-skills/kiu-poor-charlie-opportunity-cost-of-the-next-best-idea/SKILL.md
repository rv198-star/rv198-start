---
name: kiu-poor-charlie-opportunity-cost-of-the-next-best-idea
description: Use this KiU-generated action skill from Poor Charlie's Almanack when the task matches `opportunity-cost-of-the-next-best-idea`.
---

# Opportunity Cost of the Next Best Idea

## Identity
```yaml
skill_id: opportunity-cost-of-the-next-best-idea
title: Opportunity Cost of the Next Best Idea
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 3
```

## Contract
```yaml
trigger:
  patterns:
  - user_comparing_new_investment_with_existing_capital_uses
  - user_considering_switching_or_redeploying_position
  exclusions:
  - no_next_best_benchmark_is_available
  - user_request_is_non_investing_decision
intake:
  required:
  - name: new_idea
    type: string
    description: The proposed new capital deployment.
  - name: next_best_existing_option
    type: string
    description: The best live alternative available right now.
  - name: switch_costs
    type: structured
    description: Taxes, friction, and foregone compounding costs.
judgment_schema:
  output:
    type: structured
    schema:
      benchmark_winner: enum[new_idea, next_best_existing_option, insufficient_information]
      benchmark_reason: string
      followup_information: list[string]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - user_compares_against_idle_cash_instead_of_next_best_alternative
  - no_switch_costs_or_benchmark_inputs_are_provided
  do_not_fire_when:
  - no_next_best_benchmark_is_available
  - user_request_is_non_investing_decision
```

## Rationale
This skill prevents capital allocation from being judged in isolation. Every new idea must be compared against a live next-best use of capital after tax, friction, compounding runway, attention cost, and switching risk are included; otherwise the user is not making a ranking decision at all, only reacting to novelty. If the benchmark is missing, stale, or obviously weaker than the true next-best alternative, the correct output is to pause and rebuild the comparison set rather than letting the new story win by default.[^anchor:opportunity-source-note] The no-benchmark adversarial case shows how isolated attractiveness can masquerade as edge, while the Costco benchmark trace shows that disciplined switching requires a live comparator that the user is genuinely willing to keep if the newcomer does not clear the hurdle.[^anchor:opportunity-eval] [^trace:canonical/costco-next-best-idea.yaml]

### Downstream Use Check
This skill must make the trade-off visible: state the chosen option, the next-best alternative, the evidence that makes the comparison decision-relevant, and the handoff question that would change the ranking.

Minimum Pressure Pass (alternative pressure): Force one cheaper, safer, or higher-optionality alternative into view; if the alternative wins under the user's stated constraint, return the trade-off rather than defending the first option. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
Three canonical traces define the benchmark discipline. `costco-next-best-idea` shows the primary pattern: compare the new idea against the best live deployable alternative, not against idle cash.[^trace:canonical/costco-next-best-idea.yaml] `capital-switching-benchmark` shows how taxes, friction, and switching costs must be included before capital is redeployed.[^trace:canonical/capital-switching-benchmark.yaml] `dexter-shoe-consideration` shows the negative lesson: a deal can look cheap in isolation and still lose once real internal alternatives are kept alive as comparators.[^trace:canonical/dexter-shoe-consideration.yaml] The source note and shared adversarial evaluation connect these traces back to one claim: opportunity cost is only real when the benchmark is live, explicit, and decision-relevant.[^anchor:opportunity-source-note] [^anchor:opportunity-eval]

The v0.2 seed preserves graph/source double anchoring and records the workflow-vs-agentic routing decision in `candidate.yaml`.

Scenario-family anchor coverage: `should_trigger` `switch-vs-compounder` -> `opportunity-source-note`, `opportunity-trace` (这是真实的 capital ranking，而不是孤立评估一个新故事。); `should_trigger` `redeploy-after-friction` -> `opportunity-trace`, `opportunity-eval` (机会成本必须带着税、摩擦和放弃的复利来算，不能只看新机会本身。); `should_not_trigger` `no-live-benchmark` -> `opportunity-eval` (没有 live benchmark，就不是 opportunity-cost judgment，只能先补比较集。); `edge_case` `benchmark-exists-but-switch-costs-unclear` -> `opportunity-source-note`, `opportunity-eval` (benchmark 在，但 switching friction 还没纳入，结论容易被新故事偷走。); `refusal` `cash-as-fake-benchmark` -> `opportunity-source-note`, `opportunity-eval` (现金不是自动的 next-best idea，除非它真的是当前最优可保留选项。).

Graph-to-skill distillation: `INFERRED` graph links `e_opportunity_google_inferred_benchmark` (`Opportunity cost of the next best idea` -> `Google omission`, source_location `sources/opportunity-cost-of-the-next-best-idea.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_capital_allocation`/Capital allocation; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先写 next_best_alternative，再比较 expected_value_delta、irreversibility 和 learning_value，最后给 switch / keep / defer。

## Relations
```yaml
depends_on:
- circle-of-competence
delegates_to: []
constrained_by:
- margin-of-safety-sizing
complements:
- invert-the-problem
- bias-self-audit
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Graph-to-skill distillation: `INFERRED` graph links `e_opportunity_google_inferred_benchmark` (`Opportunity cost of the next best idea` -> `Google omission`, source_location `sources/opportunity-cost-of-the-next-best-idea.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_capital_allocation`/Capital allocation; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先写 next_best_alternative，再比较 expected_value_delta、irreversibility 和 learning_value，最后给 switch / keep / defer。

Scenario families:
- `should_trigger` `switch-vs-compounder`; 当用户在一个新想法和现有最佳资本用途之间做切换或再配置时触发。; signals: 要不要把仓位换过去 / 新机会看起来更刺激 / 现有持仓和新想法怎么选; boundary: 这是真实的 capital ranking，而不是孤立评估一个新故事。; next: 把 new idea、next-best existing option、switch costs、tax friction 和放弃复利的代价并列写出，再决定 keep / switch / insufficient_information。
- `should_trigger` `redeploy-after-friction`; 当用户考虑卖出现有仓位、收购已有业务或从成熟复利资产切去新标的时触发。; signals: 税费怎么算 / 切换成本 / 卖掉现有仓位去买新机会; boundary: 机会成本必须带着税、摩擦和放弃的复利来算，不能只看新机会本身。; next: 先把税、摩擦、时间成本和放弃的 compounding runway 写成 benchmark reason，再判断新想法是否真的胜出。
- `should_trigger` `graph-inferred-link-e_opportunity_google_inferred_benchmark`; Graph-to-skill distillation: `INFERRED` edge `e_opportunity_google_inferred_benchmark` expands trigger language only when a live decision links `Opportunity cost of the next best idea` and `Google omission`.; signals: Opportunity cost of the next best idea / Google omission / # Opportunity Cost of the Next Best Idea Source Note Skill ID: opportunity-co...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 先写 next_best_alternative，再比较 expected_value_delta、irreversibility 和 learning_value，最后给 switch / keep / defer。 Evidence check: verify source_location `sources/opportunity-cost-of-the-next-best-idea.md:1-9` before expanding the trigger.
- `should_not_trigger` `no-live-benchmark`; 当用户只有一个新想法，却没有真实 next-best alternative 时不应触发为完整基准比较。; signals: 先看看这个机会怎么样 / 暂时没有别的选择 / 先不比较现有持仓; boundary: 没有 live benchmark，就不是 opportunity-cost judgment，只能先补比较集。
- `edge_case` `benchmark-exists-but-switch-costs-unclear`; 用户知道新想法和旧仓位要比，但还没把税费、时间成本和复利中断写清时，只能部分适用。; signals: 大概能换过去 / 税费还没算 / 先粗略比较一下; boundary: benchmark 在，但 switching friction 还没纳入，结论容易被新故事偷走。; next: 先补税费、交易摩擦、注意力成本和放弃的复利，再决定是不是继续比较。
- `refusal` `cash-as-fake-benchmark`; 当用户把现金、模糊乐观或空白状态当成 next-best benchmark 时拒绝给出胜负结论。; signals: 反正现在也没买别的 / 先和空仓比 / 现金放着也没用; boundary: 现金不是自动的 next-best idea，除非它真的是当前最优可保留选项。; next: 明确指出 benchmark 缺失，要求重建 live alternative set，而不是让新想法默认获胜。

Representative cases:
- `traces/canonical/costco-next-best-idea.yaml`
- `traces/canonical/capital-switching-benchmark.yaml`
- `traces/canonical/dexter-shoe-consideration.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=18 / total=20, threshold=0.7, status=`under_evaluation`
- `synthetic_adversarial`: passed=18 / total=20, threshold=0.85, status=`under_evaluation`
- `out_of_distribution`: passed=9 / total=10, threshold=0.9, status=`under_evaluation`

关键失败模式：
- Users often compare a new idea to cash instead of a real next-best opportunity.
- Users can keep the benchmark so vague that switching costs and foregone compounding never enter the comparison.
- Story strength can overwhelm ranking discipline unless the next-best alternative remains live and explicit.

场景族覆盖：`should_trigger`=3，`should_not_trigger`=1，`edge_case`=1，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Add richer real redeployment cases with explicit tax and friction data in future bundle versions.
- Run a real refinement_scheduler pass before describing this skill as loop-driven.


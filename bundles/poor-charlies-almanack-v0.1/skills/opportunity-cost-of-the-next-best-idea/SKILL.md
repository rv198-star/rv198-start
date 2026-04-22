# Opportunity Cost of the Next Best Idea

## Identity
```yaml
skill_id: opportunity-cost-of-the-next-best-idea
title: Opportunity Cost of the Next Best Idea
status: published
bundle_version: 0.1.0
skill_revision: 4
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

## Evidence Summary
Three canonical traces define the benchmark discipline. `costco-next-best-idea` shows the primary pattern: compare the new idea against the best live deployable alternative, not against idle cash.[^trace:canonical/costco-next-best-idea.yaml] `capital-switching-benchmark` shows how taxes, friction, and switching costs must be included before capital is redeployed.[^trace:canonical/capital-switching-benchmark.yaml] `dexter-shoe-consideration` shows the negative lesson: a deal can look cheap in isolation and still lose once real internal alternatives are kept alive as comparators.[^trace:canonical/dexter-shoe-consideration.yaml] The source note and shared adversarial evaluation connect these traces back to one claim: opportunity cost is only real when the benchmark is live, explicit, and decision-relevant.[^anchor:opportunity-source-note] [^anchor:opportunity-eval]

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

Representative cases:
- `traces/canonical/costco-next-best-idea.yaml`
- `traces/canonical/capital-switching-benchmark.yaml`
- `traces/canonical/dexter-shoe-consideration.yaml`

## Evaluation Summary
The full v0.1 shared evaluation corpus remains attached through release-scale bindings. The current summary covers 20 real decisions, 20 adversarial traps, and 10 OOD refusals; the dominant failure cluster is still users comparing a new idea against cash, vibes, or generic optimism rather than against a live next-best benchmark with switching costs included. See `eval/summary.yaml`.

## Revision Summary
Revision 4 upgrades opportunity-cost-of-the-next-best-idea to the v0.4 content standard: the rationale now makes live ranking and switching friction explicit, the evidence summary names three canonical traces directly, and the relations now connect benchmark comparison to inversion and bias review instead of leaving it isolated. The remaining gap is to propagate the same rewrite depth across the rest of the published bundle. See `iterations/revisions.yaml`.

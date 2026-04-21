# Opportunity Cost of the Next Best Idea

## Identity
```yaml
skill_id: opportunity-cost-of-the-next-best-idea
title: Opportunity Cost of the Next Best Idea
status: under_evaluation
bundle_version: 0.1.0
skill_revision: 1
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
This skill stops isolated idea evaluation from hijacking capital allocation. A new idea has to beat a live next-best option after friction and foregone compounding are counted.

## Evidence Summary
The core anchors are the opportunity-cost source note plus the Costco benchmark trace, with Google omission and Dexter Shoe retained as supporting scenarios. Graph anchors bind the skill to the capital-allocation community.

## Relations
```yaml
depends_on:
  - circle-of-competence
delegates_to: []
constrained_by:
  - margin-of-safety-sizing
complements:
  - bias-self-audit
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/costco-next-best-idea.yaml`
- `traces/canonical/google-omission.yaml`
- `traces/canonical/dexter-shoe-consideration.yaml`

## Evaluation Summary
The reference eval set proves the contract shape, but publication is deferred until more real switching cases are attached. The current weak point is users failing to name a real next-best benchmark. See `eval/summary.yaml`.

## Revision Summary
Revision 1 establishes the benchmark-first contract and the refusal rule for missing next-best alternatives. See `iterations/revisions.yaml`.

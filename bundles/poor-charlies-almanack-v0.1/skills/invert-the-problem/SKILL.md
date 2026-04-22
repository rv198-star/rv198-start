# Invert the Problem

## Identity
```yaml
skill_id: invert-the-problem
title: Invert the Problem
status: published
bundle_version: 0.1.0
skill_revision: 4
```

## Contract
```yaml
trigger:
  patterns:
    - user_planning_a_high_stakes_action_path
    - user_stuck_in_complex_success_planning
  exclusions:
    - user_request_is_pure_fact_lookup
    - user_outcome_is_already_decided
intake:
  required:
    - name: objective
      type: string
      description: Outcome the user wants to achieve.
    - name: constraints
      type: list
      description: Known constraints, irreversibilities, and deadlines.
judgment_schema:
  output:
    type: structured
    schema:
      failure_modes: list[string]
      avoid_rules: list[string]
      first_preventive_action: string
  reasoning_chain_required: true
boundary:
  fails_when:
    - user_treats_inversion_as_complete_strategy_without_followup
    - input_lacks_a_concrete_objective_or_constraint_set
  do_not_fire_when:
    - user_request_is_pure_fact_lookup
    - user_outcome_is_already_decided
```

## Rationale
Inversion is a failure-map, not decorative "think backwards" advice. The evaluator should force the user to name the ruin conditions, single-point failures, hidden assumptions, irreversible losses, and objective confusions that would make the plan fail before anyone optimizes a forward path. If the user already knows the answer and only wants a confidence ritual, the skill should not reward that posture with a generic checklist; it should expose the missing avoid-rules, the undefended downside, or the fact that the objective is still too vague to optimize safely.[^anchor:invert-source-note] The zero-buffer adversarial case shows why a coherent forward thesis can still fail the survival test, while the anti-ruin trace shows that inversion earns its keep only when it produces explicit no-go conditions that change the action path.[^anchor:invert-eval] [^trace:canonical/anti-ruin-checklist.yaml]

## Evidence Summary
Three canonical traces define the operating pattern. `anti-ruin-checklist` shows the basic move: list the failure conditions first, then remove the largest ones before discussing upside.[^trace:canonical/anti-ruin-checklist.yaml] `pilot-pre-mortem` shows inversion handing work to a later audit by delaying commitment until incentives and single-point failures become visible.[^trace:canonical/pilot-pre-mortem.yaml] `airline-bankruptcy-checklist` shows why this skill must block narrative optimism when the ruin chain is still intact.[^trace:canonical/airline-bankruptcy-checklist.yaml] The source note and shared adversarial evaluation tie those traces to one claim: inversion is valuable when it changes the decision boundary through explicit avoid-rules, not when it merely restates the original plan with different words.[^anchor:invert-source-note] [^anchor:invert-eval]

## Relations
```yaml
depends_on: []
delegates_to:
  - bias-self-audit
constrained_by:
  - circle-of-competence
complements:
  - margin-of-safety-sizing
  - opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/anti-ruin-checklist.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`
- `traces/canonical/airline-bankruptcy-checklist.yaml`

## Evaluation Summary
KiU Test is green and the full v0.1 shared evaluation corpus remains attached through release-scale bindings. The current summary covers 20 real decisions, 20 adversarial traps, and 10 OOD refusals; the main failure cluster is forward planning that sounds coherent but never names the ruin path, plus already-decided actions trying to use inversion as post-hoc decoration. See `eval/summary.yaml`.

## Revision Summary
Revision 4 upgrades inversion to the v0.4 content standard: the rationale now enforces failure-map outputs instead of generic brainstorming, the evidence summary names three canonical traces explicitly, and the relations now show how inversion is bounded by domain competence and complements later sizing and benchmark work. The remaining gap is to mirror the same depth across the rest of the published bundle. See `iterations/revisions.yaml`.

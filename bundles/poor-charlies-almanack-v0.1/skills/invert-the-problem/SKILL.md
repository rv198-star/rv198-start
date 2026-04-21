# Invert the Problem

## Identity
```yaml
skill_id: invert-the-problem
title: Invert the Problem
status: published
bundle_version: 0.1.0
skill_revision: 2
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
Inversion is an error-prevention skill. It is most useful when forward optimization is too fuzzy and the first useful move is to list what would guarantee failure.

## Evidence Summary
The reference evidence combines the inversion source note with the anti-ruin checklist and pre-mortem traces. Graph anchors bind the skill to the error-avoidance community in the published graph.

## Relations
```yaml
depends_on: []
delegates_to:
  - bias-self-audit
constrained_by: []
complements:
  - margin-of-safety-sizing
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/anti-ruin-checklist.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`
- `traces/canonical/airline-bankruptcy-checklist.yaml`

## Evaluation Summary
KiU Test is green and the full v0.1 shared evaluation corpus is attached. The published summary covers four real-decision cases, four adversarial traps, and two OOD refusals for inversion-style dispatch. See `eval/summary.yaml`.

## Revision Summary
Revision 2 promotes the skill to `published` after adding a third canonical trace and expanding the eval set from sample coverage to release coverage. See `iterations/revisions.yaml`.

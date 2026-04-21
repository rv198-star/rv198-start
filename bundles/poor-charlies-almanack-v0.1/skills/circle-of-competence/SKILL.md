# Circle of Competence

## Identity
```yaml
skill_id: circle-of-competence
title: Circle of Competence
status: published
bundle_version: 0.1.0
skill_revision: 2
```

## Contract
```yaml
trigger:
  patterns:
    - user_considering_specific_investment
    - user_asking_if_understanding_is_deep_enough_to_act
  exclusions:
    - user_choosing_passive_index_fund
    - user_request_is_non_investing_decision
intake:
  required:
    - name: target
      type: entity
      description: Asset, company, or domain under consideration.
    - name: user_background
      type: structured
      description: Demonstrated exposure and depth in the target domain.
    - name: capital_at_risk
      type: number
      description: Share of net worth or portfolio at stake.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[in_circle, edge_of_circle, outside_circle]
      missing_knowledge: list[string]
      recommended_action: enum[proceed, study_more, decline]
  reasoning_chain_required: true
boundary:
  fails_when:
    - user_confuses_product_familiarity_with_business_understanding
    - user_describes_background_too_vaguely_to_test_depth
  do_not_fire_when:
    - user_chooses_passive_index_fund
    - user_request_is_non_investing_decision
```

## Rationale
This skill turns "stay in your circle" into an explicit refusal contract. It should push users toward `study_more` or `decline` whenever the understanding gap is material relative to the decision size.

## Evidence Summary
The core evidence comes from the local source note plus three canonical traces: dotcom refusal, Google omission, and crypto rejection. See `anchors.yaml` for the graph snapshot binding and file-level evidence anchors.

## Relations
```yaml
depends_on: []
delegates_to:
  - bias-self-audit
constrained_by:
  - margin-of-safety-sizing
complements:
  - opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/dotcom-refusal.yaml`
- `traces/canonical/google-omission.yaml`
- `traces/canonical/crypto-rejection.yaml`

## Evaluation Summary
KiU Test is green and the full v0.1 shared evaluation corpus is now attached. The published summary covers four real-decision cases, four adversarial traps, and two OOD refusals, with the main failure mode still centered on surface familiarity masquerading as expertise. See `eval/summary.yaml`.

## Revision Summary
Revision 2 closes the v0.1 publication loop: tightened exclusions for passive indexing, preserved the graph/source anchor binding, and expanded the attached eval set to full-release scale. See `iterations/revisions.yaml`.

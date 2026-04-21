# Bias Self Audit

## Identity
```yaml
skill_id: bias-self-audit
title: Bias Self Audit
status: published
bundle_version: 0.1.0
skill_revision: 2
```

## Contract
```yaml
trigger:
  patterns:
    - user_about_to_commit_high_stakes_investment_decision
    - user_expressing_unusual_certainty_or_social_pressure
  exclusions:
    - decision_is_low_stakes_or_reversible
    - user_request_is_non_investing_decision
intake:
  required:
    - name: thesis
      type: string
      description: The current decision thesis in the user's own words.
    - name: incentives
      type: list
      description: Incentives, identity, or social forces that could bias the user.
    - name: reversibility
      type: string
      description: How costly it is to reverse the decision.
judgment_schema:
  output:
    type: structured
    schema:
      triggered_biases: list[string]
      severity: enum[low, medium, high]
      mitigation_actions: list[string]
  reasoning_chain_required: true
boundary:
  fails_when:
    - user_tries_to_use_bias_audit_as_domain_analysis
    - decision_is_too_low_stakes_to_warrant_full_audit
  do_not_fire_when:
    - decision_is_low_stakes_or_reversible
    - user_request_is_non_investing_decision
```

## Rationale
The skill exists to force an explicit anti-bias pass before irreversible commitments. It should name the likely bias cluster and prescribe mitigations rather than merely reminding the user to "be careful."

## Evidence Summary
The strongest anchors are the bias source note, the US Air regret trace, and the shared TSLA surface-familiarity adversarial case. Graph anchors place the skill in both the boundary-discipline and error-avoidance evidence neighborhoods.

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by:
  - circle-of-competence
complements:
  - invert-the-problem
  - opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/us-air-regret.yaml`
- `traces/canonical/incentive-caused-delusion-audit.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`

## Evaluation Summary
The full v0.1 evaluation corpus is attached and published. The remaining calibration question is not whether the skill is ready to ship, but how strict later versions should become around low-stakes refusals. See `eval/summary.yaml`.

## Revision Summary
Revision 2 promotes the skill to `published` after adding a stronger incentive-bias trace and expanding the evaluation set to release scale. See `iterations/revisions.yaml`.

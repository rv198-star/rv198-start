# Bias Self Audit

## Identity
```yaml
skill_id: bias-self-audit
title: Bias Self Audit
status: published
bundle_version: 0.1.0
skill_revision: 4
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
This skill converts "watch your biases" from empty hygiene language into a pre-commitment audit log. The evaluator should name the active distortion cluster, tie it to incentives, identity, sunk cost, social proof, or time pressure, and then require a concrete countermeasure such as disconfirming evidence, an external base rate, an outside reviewer, or a smaller position. If the user cannot specify what bias is active right now, the safe assumption is that confidence has outrun self-observation and that the decision should slow down before more commitment is made.[^anchor:bias-source-note] The shared adversarial familiarity case shows how confidence can hide attachment behind a persuasive story, while the US Air trace shows why retrospective regret is too late if no explicit audit existed before capital was committed.[^anchor:bias-eval] [^trace:canonical/us-air-regret.yaml]

## Evidence Summary
Three canonical traces define the audit pattern. `us-air-regret` shows the anti-pattern: a neat thesis can conceal overconfidence and incentive blindness until the mistake is already locked in.[^trace:canonical/us-air-regret.yaml] `incentive-caused-delusion-audit` shows the positive pattern: pause the decision and force a written audit when compensation or identity exposure is distorting interpretation.[^trace:canonical/incentive-caused-delusion-audit.yaml] `pilot-pre-mortem` shows why bias review often belongs after inversion has exposed the failure chain but before the team treats the thesis as settled.[^trace:canonical/pilot-pre-mortem.yaml] The source note and shared adversarial evaluation connect these traces back to one claim: bias is only actionable when the distortion and mitigation are named explicitly before commitment hardens.[^anchor:bias-source-note] [^anchor:bias-eval]

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by:
  - circle-of-competence
complements:
  - invert-the-problem
  - margin-of-safety-sizing
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
The full v0.1 shared evaluation corpus remains attached through release-scale bindings. The current summary covers 20 real decisions, 20 adversarial traps, and 10 OOD refusals; the main calibration issue is still low-stakes false positives, plus cases where users can describe the thesis fluently but still cannot name the incentive or identity pressure acting on them. See `eval/summary.yaml`.

## Revision Summary
Revision 4 upgrades bias-self-audit to the v0.4 content standard: the rationale now demands named distortions and countermeasures, the evidence summary names three canonical traces explicitly, and the relations now show how bias review fits between inversion, sizing, and benchmark comparison. The remaining gap is to propagate the same rewrite depth across the rest of the published bundle. See `iterations/revisions.yaml`.

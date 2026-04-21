# Margin of Safety Sizing

## Identity
```yaml
skill_id: margin-of-safety-sizing
title: Margin of Safety Sizing
status: published
bundle_version: 0.1.0
skill_revision: 2
```

## Contract
```yaml
trigger:
  patterns:
    - user_deciding_position_size_for_investment
    - user_contemplating_concentrated_capital_allocation
  exclusions:
    - user_missing_uncertainty_inputs
    - user_request_is_non_investing_decision
intake:
  required:
    - name: downside_range
      type: structured
      description: Estimated downside range and ruin conditions.
    - name: liquidity_profile
      type: structured
      description: Liquidity, reversibility, and access to fallback capital.
    - name: conviction_basis
      type: string
      description: Why the user believes the edge exists.
judgment_schema:
  output:
    type: structured
    schema:
      sizing_band: enum[tiny, small, medium, concentrated, refuse]
      constraints: list[string]
      rationale: string
  reasoning_chain_required: true
boundary:
  fails_when:
    - user_asserts_high_conviction_without_downside_math
    - liquidity_or_ruin_inputs_are_missing
  do_not_fire_when:
    - user_request_is_non_investing_decision
    - user_missing_uncertainty_inputs
```

## Rationale
The skill turns "margin of safety" into exposure guidance rather than a slogan. It should shrink position size when the error bars, leverage, or liquidity profile make survival fragile.

## Evidence Summary
The reference bundle anchors this skill to the risk-control community with See's Candies discipline and Salomon exposure capping as shared traces. The source note explicitly states that sizing is part of the margin-of-safety contract.

## Relations
```yaml
depends_on:
  - circle-of-competence
delegates_to: []
constrained_by:
  - invert-the-problem
complements:
  - opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Representative cases:
- `traces/canonical/sees-candies-discipline.yaml`
- `traces/canonical/salomon-exposure-cap.yaml`
- `traces/canonical/irreversible-bet-precheck.yaml`

## Evaluation Summary
The full v0.1 evaluation corpus is attached and published. The dominant failure mode remains users presenting conviction without downside, liquidity, or ruin math. See `eval/summary.yaml`.

## Revision Summary
Revision 2 promotes the skill to `published` after expanding the sizing cases from a sample gate to a release-scale corpus. See `iterations/revisions.yaml`.

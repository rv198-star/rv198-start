# Margin of Safety Sizing

## Identity
```yaml
skill_id: margin-of-safety-sizing
title: Margin of Safety Sizing
status: published
bundle_version: 0.1.0
skill_revision: 4
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
This skill makes margin of safety operational at the sizing layer rather than leaving it trapped inside valuation talk. The evaluator should ask how wrong the thesis can be, what happens to liquidity under stress, whether leverage or correlation can force selling, and how much optionality survives if the user is early, late, or simply mistaken. If the downside path includes refinancing dependence, concentrated illiquidity, or zero cash buffer, the correct output is to shrink size or refuse the position even when the upside narrative remains emotionally persuasive.[^anchor:margin-source-note] The zero-buffer adversarial case shows why conviction alone is not a sizing input, and the Salomon trace shows that survival is protected by capping exposure before the balance sheet loses flexibility, not by improvising after pressure arrives.[^anchor:margin-eval] [^trace:canonical/salomon-exposure-cap.yaml]

## Evidence Summary
Three canonical traces define the sizing discipline. `sees-candies-discipline` shows that quality only earns concentration when downside resilience and business durability are both explicit.[^trace:canonical/sees-candies-discipline.yaml] `salomon-exposure-cap` shows that exposure limits are a survival tool for leveraged or reputation-sensitive situations, not a sign of weak conviction.[^trace:canonical/salomon-exposure-cap.yaml] `irreversible-bet-precheck` shows how irreversibility and unwind friction should compress size even before the user reaches a hard refusal.[^trace:canonical/irreversible-bet-precheck.yaml] The source note and shared adversarial evaluation tie these traces back to one claim: margin of safety is about preserving survival and optionality under uncertainty, not decorating a bullish thesis with cautious language.[^anchor:margin-source-note] [^anchor:margin-eval]

## Relations
```yaml
depends_on:
  - circle-of-competence
delegates_to: []
constrained_by:
  - invert-the-problem
complements:
  - bias-self-audit
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
The full v0.1 shared evaluation corpus remains attached through release-scale bindings. The current summary covers 20 real decisions, 20 adversarial traps, and 10 OOD refusals; the main failure cluster is still conviction without downside, liquidity, or ruin math, especially when users confuse valuation upside with permission to size aggressively. See `eval/summary.yaml`.

## Revision Summary
Revision 4 upgrades margin-of-safety-sizing to the v0.4 content standard: the rationale now makes survival and optionality the explicit output criterion, the evidence summary names three canonical traces directly, and the relations now show how sizing interacts with bias review and live-alternative benchmarking. The remaining gap is to propagate the same rewrite depth across the rest of the published bundle. See `iterations/revisions.yaml`.

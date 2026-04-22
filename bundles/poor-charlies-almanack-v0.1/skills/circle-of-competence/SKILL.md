# Circle of Competence

## Identity
```yaml
skill_id: circle-of-competence
title: Circle of Competence
status: published
bundle_version: 0.1.0
skill_revision: 4
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
This skill is a boundary-enforcement routine for capital allocation, not a generic humility slogan. The evaluator should force the user to explain revenue drivers, cost structure, industry structure, management incentives, likely failure modes, and what evidence would falsify the thesis, then compare that demonstrated explanatory depth with the percentage of capital and irreversibility at stake. If the claimed understanding collapses into product love, ticker familiarity, expert-name borrowing, or vague confidence about a trend, the correct judgment is `outside_circle` or `edge_of_circle`, followed by `study_more` or `decline`, because missing knowledge is still doing real work in the decision.[^anchor:circle-source-note] The biotech-founder real-decision case and the surface-familiarity adversarial case show that education, ownership, and daily product use can all generate false confidence without producing business understanding, while the refusal traces show that disciplined non-action is itself a positive output when capital at risk is material.[^anchor:circle-eval] [^trace:canonical/dotcom-refusal.yaml]

## Evidence Summary
Three canonical traces make the skill concrete. `dotcom-refusal` shows the clean refusal pattern: when the category cannot be explained with cash-flow and industry clarity, the right move is to pass rather than improvise conviction.[^trace:canonical/dotcom-refusal.yaml] `google-omission` shows the harder case: even when the eventual outcome is excellent, a pass can still be correct if the durable economics were not truly understood at decision time; that keeps the skill anchored to process quality instead of hindsight envy.[^trace:canonical/google-omission.yaml] `crypto-rejection` shows the extreme boundary case: when there is no intelligible business model to analyze, the absence of a value engine is itself a reason to refuse participation.[^trace:canonical/crypto-rejection.yaml] The source note and shared adversarial evaluation connect these traces back to the same core judgment: do not let familiarity, narrative heat, or outcome regret masquerade as demonstrated competence.[^anchor:circle-source-note] [^anchor:circle-eval]

## Relations
```yaml
depends_on: []
delegates_to:
  - bias-self-audit
constrained_by:
  - margin-of-safety-sizing
complements:
  - invert-the-problem
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
KiU Test is green and the full v0.1 shared evaluation corpus remains attached through release-scale bindings. The current summary covers 20 real decisions, 20 adversarial traps, and 10 OOD refusals; the dominant failure cluster is still false-positive confidence from product familiarity, elite credentials outside domain, and hindsight regret over omitted winners. See `eval/summary.yaml`.

## Revision Summary
Revision 4 turns this skill into the v0.4 reference pattern: the rationale now tests demonstrated explanatory depth instead of generic humility, the evidence summary names three canonical traces explicitly, and the relations now connect circle discipline to inversion and next-best benchmarking. The remaining gap is to propagate the same depth and evidence explicitness to the other four published investing skills. See `iterations/revisions.yaml`.

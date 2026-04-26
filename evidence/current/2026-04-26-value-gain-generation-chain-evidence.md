# Value-Gain Generation Chain Evidence

Date: 2026-04-26
Evidence level: internal deterministic five-book rerun. This is not external user validation.

## Purpose

The external value-gain methodology was previously documented only as an audit tool and tested through temporary A/B patches. This evidence records the first implementation that fixes the gap: value-gain checks are now emitted by the default SKILL generation chain instead of being added after generation.

## Implementation Boundary

The implementation lives in `src/kiu_pipeline/draft.py` inside `build_candidate_skill_markdown`.

It adds a generation-time enhancer that:

- Extends `judgment_schema.output.schema` with `value_gain_decision`, `value_gain_evidence`, `value_gain_risk_boundary`, and `value_gain_next_handoff`.
- Appends a `### Downstream Use Check` subsection to the Rationale.
- Varies the check by skill shape, such as workflow gateway, bias audit, risk sizing, opportunity-cost, and value/source-anchor skills.
- Does not write external methodology names into generated source-derived `SKILL.md` artifacts.

## Five-Book Rerun

Run root: `/tmp/kiu-v081-value-gain-chain-20260426-2230`

| Book | Run root | Source | Generated | Usage | Overall | Gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Financial Statement | `/tmp/kiu-v081-value-gain-chain-20260426-2230/financial/generated/financial-statement-source-v0.6/value-gain-financial` | 88.1 | 94.3 | 97.9 | 93.5 | PASS |
| Effective Requirements | `/tmp/kiu-v081-value-gain-chain-20260426-2230/effective/generated/effective-requirements-source-v0.6/value-gain-effective` | 92.9 | 94.3 | 97.9 | 95.0 | PASS |
| Mao Anthology | `/tmp/kiu-v081-value-gain-chain-20260426-2230/mao/generated/mao-source-v0.6/value-gain-mao` | 94.2 | 94.3 | 97.0 | 95.1 | PASS |
| Poor Charlie | `/tmp/kiu-v081-value-gain-chain-20260426-2230/poor/generated/poor-charlies-almanack-v0.1/value-gain-poor-charlie` | 100.0 | 97.8 | 95.8 | 97.9 | PASS |
| Shiji | `/tmp/kiu-v081-value-gain-chain-20260426-2230/shiji/generated/shiji-source-v0.6/value-gain-shiji` | 94.0 | 96.4 | 95.8 | 95.5 | PASS |

## Marker Coverage

Marker scan counted `Downstream Use Check` and the four `value_gain_*` output fields under generated `bundle/skills`:

| Book | Marker count |
| --- | ---: |
| Financial Statement | 15 |
| Effective Requirements | 15 |
| Mao Anthology | 30 |
| Poor Charlie | 30 |
| Shiji | 15 |

Pollution scan for `模块价值增益法` and `thinking-value-gain` under the five generated runs returned no matches.

## Tests

Targeted TDD test:

- `PYTHONPATH=src .venv/bin/python -m unittest tests.test_pipeline.CandidatePipelineTests.test_generated_skills_include_value_gain_contract_without_external_method_pollution -v`
- Result: OK

Regression:

- `PYTHONPATH=src .venv/bin/python -m unittest discover tests -v`
- Result: `Ran 281 tests in 26.147s`, `OK`.

## Interpretation

The value-gain layer is now part of the default generated SKILL chain. It preserves release gates and current three-layer scores across the five established sample books.

The current automatic scoring still does not assign extra points for the added downstream usability fields, so this evidence supports structural integration and no-regression, not a quantified user-value uplift.


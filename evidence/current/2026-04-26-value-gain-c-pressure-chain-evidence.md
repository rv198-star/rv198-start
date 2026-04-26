# Value-Gain C-Version Pressure Chain Evidence

Date: 2026-04-26
Evidence level: internal deterministic five-book rerun + internal user-perspective A/B/C review. This is not external blind review or real-user validation.

## Purpose

C-version integrates the refreshed external value-gain methodology's `Minimum Pressure Pass` idea into the default generated SKILL chain. It is designed to fix the B-version weakness: too many `Downstream Use Check` sections remained generic.

## Implementation Boundary

Implementation remains in `src/kiu_pipeline/draft.py` inside `build_candidate_skill_markdown`.

C-version keeps the B-version value-gain output fields and adds a skill-sensitive pressure pass inside `### Downstream Use Check`:

- `failure pressure` for bias audit and risk/sizing skills.
- `alternative pressure` for opportunity-cost, contradiction, resistance, and tradeoff skills.
- `evidence pressure` for value/source-anchor, historical analogy, role-boundary, case, and consequence skills.
- `downstream pressure` for workflow gateway and problem-reframing style skills.

Generated SKILL artifacts do not mention `模块价值增益法`, `thinking-value-gain`, or `Premature Exit Check`. Only the operational pressure-pass wording appears in generated artifacts.

## Five-Book Rerun

Run root: `/tmp/kiu-v081-value-gain-c-chain-20260426-2305`

| Book | Run root | Source | Generated | Usage | Overall | Gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Financial Statement | `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/financial/generated/financial-statement-source-v0.6/value-gain-c-financial` | 88.1 | 94.3 | 97.9 | 93.5 | PASS |
| Effective Requirements | `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/effective/generated/effective-requirements-source-v0.6/value-gain-c-effective` | 92.9 | 94.3 | 97.9 | 95.0 | PASS |
| Mao Anthology | `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/mao/generated/mao-source-v0.6/value-gain-c-mao` | 94.2 | 94.3 | 97.0 | 95.1 | PASS |
| Poor Charlie | `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/poor/generated/poor-charlies-almanack-v0.1/value-gain-c-poor-charlie` | 100.0 | 97.8 | 95.8 | 97.9 | PASS |
| Shiji | `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/shiji/generated/shiji-source-v0.6/value-gain-c-shiji` | 94.0 | 96.4 | 95.8 | 95.5 | PASS |

Pressure marker counts under generated `bundle/skills`:

| Book | Marker count |
| --- | ---: |
| Financial Statement | 3 |
| Effective Requirements | 3 |
| Mao Anthology | 6 |
| Poor Charlie | 6 |
| Shiji | 3 |

The marker count equals one pressure pass per generated skill.

Pollution scan for `模块价值增益法`, `thinking-value-gain`, and `Premature Exit Check` under the C-version run root returned no matches.

## Internal A/B/C User-Perspective Review

Compared versions:

- A: v0.8.1 original generation, `/tmp/kiu-v081-fivebook-regression-final/`
- B: value-gain fields + generic/shape-based downstream check, `/tmp/kiu-v081-value-gain-chain-20260426-2230/`
- C: B plus `Minimum Pressure Pass`, `/tmp/kiu-v081-value-gain-c-chain-20260426-2305/`

Sample: same 10 non-workflow skill pairs used in the prior A/B review.

| Book | Skill | A total | B total | C total | C-B | Review note |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Financial Statement | `accounting-quality-signal-check` | 20.0 | 21.7 | 22.5 | +0.8 | C adds downstream missing-truth pressure. |
| Financial Statement | `business-value-anchor-check` | 20.5 | 22.5 | 23.0 | +0.5 | C preserves value/evidence separation and adds evidence-overclaim pressure. |
| Effective Requirements | `solution-to-problem-reframing` | 20.7 | 21.8 | 22.8 | +1.0 | C converts reframe into decision, owner, and missing handoff. |
| Effective Requirements | `stakeholder-resistance-tradeoff` | 20.2 | 21.3 | 22.6 | +1.3 | C adds competing-frame pressure, fixing B's generic weakness. |
| Mao Anthology | `historical-analogy-transfer-gate` | 21.3 | 22.1 | 23.0 | +0.9 | C checks mechanism evidence instead of story similarity. |
| Mao Anthology | `principal-contradiction-focus` | 20.7 | 21.6 | 22.8 | +1.2 | C adds alternative-frame pressure. |
| Poor Charlie | `bias-self-audit` | 21.6 | 23.3 | 24.0 | +0.7 | C adds failure pressure around identity, incentive, sunk cost, and consensus. |
| Poor Charlie | `margin-of-safety-sizing` | 21.7 | 23.3 | 24.0 | +0.7 | C adds worst-credible-miss pressure. |
| Shiji | `historical-analogy-transfer-gate` | 21.3 | 22.1 | 23.0 | +0.9 | Same mechanism-evidence improvement as Mao. |
| Shiji | `role-boundary-before-action` | 21.2 | 22.3 | 23.1 | +0.8 | C adds mechanism-evidence pressure for role transfer. |

Average totals:

- A: `20.92/25`
- B: `22.20/25`
- C: `23.08/25`
- B-A: `+1.28`
- C-A: `+2.16`
- C-B: `+0.88`

## Findings

Positive findings:

- C keeps all release gates green and does not change three-layer automatic scores.
- C directly addresses B's main weakness: generic downstream checks.
- C covers all four pressure families across the 10 sampled pairs.
- C improves the internal user-perspective score over both A and B.

Weaknesses:

- C still uses heuristic shape detection, not a full LLM-assisted module audit.
- Some role-boundary and historical analogy skills share the same evidence-pressure wording. This is better than B, but still not fully book-specific.
- The score remains internal review evidence, not external user validation.

## Verdict

C-version should replace B-version as the default value-gain chain.

The next improvement should not add more process weight. It should improve shape detection and source-aware wording so pressure checks become more book/skill-specific without polluting source evidence.

## Tests

Targeted tests:

- `PYTHONPATH=src .venv/bin/python -m unittest tests.test_pipeline.CandidatePipelineTests.test_generated_skills_include_value_gain_contract_without_external_method_pollution -v`
- `PYTHONPATH=src .venv/bin/python -m unittest tests.test_pipeline.CandidatePipelineTests.test_example_fixture_candidates_use_seeded_quality_content tests.test_pipeline.CandidatePipelineTests.test_preflight_accepts_generated_bundle tests.test_pipeline.CandidatePipelineTests.test_generated_skills_include_value_gain_contract_without_external_method_pollution -v`

Full regression:

- `PYTHONPATH=src .venv/bin/python -m unittest discover tests -v`
- Result: `Ran 281 tests in 26.417s`, `OK`.


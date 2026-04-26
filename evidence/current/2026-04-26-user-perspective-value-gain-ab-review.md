# User-Perspective Value-Gain A/B Review

Date: 2026-04-26
Evidence level: internal human/user-perspective review. This is not external blind review or real-user validation.

## Purpose

The value-gain layer is now emitted by the default SKILL generation chain. Automatic scoring proved no regression, but it did not measure whether the new layer is more useful to a user. This review compares old v0.8.1 outputs against the new value-gain-chain outputs from a user-facing reading perspective.

## Inputs

Old A outputs:

- `/tmp/kiu-v081-fivebook-regression-final/`

New B outputs:

- `/tmp/kiu-v081-value-gain-chain-20260426-2230/`

Sample selection: two non-workflow skills per book, 10 pairs total.

## Rubric

Each pair is scored on five 1-5 dimensions. Higher is better. For cognitive load, higher means lower burden.

- Decision clarity: does the user know what judgment or action this skill changes?
- Evidence usability: does the user know what source-backed evidence to inspect?
- Boundary safety: does the user know when not to apply or when to defer?
- Next-step executability: does the user know what to do next?
- Cognitive load: does the extra content help without making the skill too heavy?

## Pair Scores

| Book | Skill | A total | B total | Delta | Review note |
| --- | --- | ---: | ---: | ---: | --- |
| Financial Statement | `accounting-quality-signal-check` | 20.0 | 21.7 | +1.7 | B makes the user state decision change, evidence, boundary, and handoff; useful but generic. |
| Financial Statement | `business-value-anchor-check` | 20.5 | 22.5 | +2.0 | Stronger than generic because it separates value signal from value conclusion. |
| Effective Requirements | `solution-to-problem-reframing` | 20.7 | 21.8 | +1.1 | B improves handoff clarity; the added check remains broad. |
| Effective Requirements | `stakeholder-resistance-tradeoff` | 20.2 | 21.3 | +1.1 | B helps force a next action but does not yet model stakeholder-specific tradeoff deeply. |
| Mao Anthology | `historical-analogy-transfer-gate` | 21.3 | 22.1 | +0.8 | B helps execution framing, but the check is still generic for analogy-transfer. |
| Mao Anthology | `principal-contradiction-focus` | 20.7 | 21.6 | +0.9 | B improves next-step framing; needs contradiction-specific value-gain wording. |
| Poor Charlie | `bias-self-audit` | 21.6 | 23.3 | +1.7 | Strong positive: B turns audit into an explicit decision brake and resume condition. |
| Poor Charlie | `margin-of-safety-sizing` | 21.7 | 23.3 | +1.6 | Strong positive: B turns caution into executable risk boundary and sizing/deferral action. |
| Shiji | `historical-analogy-transfer-gate` | 21.3 | 22.1 | +0.8 | Same pattern as Mao: useful handoff gain, weak differentiation. |
| Shiji | `role-boundary-before-action` | 21.2 | 22.3 | +1.1 | B improves apply/defer handoff; needs role-boundary-specific wording. |

## Dimension Averages

| Dimension | A avg | B avg | Delta | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Decision clarity | 4.24 | 4.67 | +0.43 | Clear positive. |
| Evidence usability | 4.22 | 4.31 | +0.09 | Mostly unchanged because source evidence was already strong. |
| Boundary safety | 4.32 | 4.55 | +0.23 | Positive but not transformational. |
| Next-step executability | 3.80 | 4.60 | +0.80 | Main value gain. |
| Cognitive load | 4.34 | 4.07 | -0.27 | Added content costs some reading weight. |

Average total score improves from `20.92/25` to `22.20/25`, a `+1.28` average gain.

## Findings

Positive findings:

- B is consistently better across all 10 sampled pairs.
- The strongest user-facing gain is next-step executability.
- Poor Charlie shows the best pattern because the enhancer detects bias and risk-sizing shapes and writes more specific checks.
- No sampled pair shows a net negative score despite the extra text.

Weaknesses:

- 8 of 10 sampled pairs still use a broad generic downstream-use check.
- Evidence usability barely improves because the value-gain layer currently points to evidence conceptually, but does not name concrete anchors beyond what the existing skill already provides.
- Cognitive load worsens slightly. The added section is short enough to remain acceptable, but it must earn its keep with stronger specificity.

## Verdict

Keep the value-gain layer in the generation chain. It produces a measurable internal user-perspective gain and does not break release gates.

Do not claim external user validation. The current result supports a follow-up A/B/C experiment: compare the current generic-plus-shape heuristic against a stronger methodology-assisted variant that produces book/skill-specific downstream checks.


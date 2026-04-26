# User-Facing Evaluation Guide

KiU has many internal checks, but users usually care about six questions.

| User-facing dimension | User question | Related internal evidence |
| --- | --- | --- |
| Source trust | Did the skill stay faithful to the source? | Source fidelity, anchors, source pollution checks, extraction kind. |
| Action helpfulness | Does the skill help me judge, choose, refuse, act, or recalibrate? | Action-value evaluation, usage review, action-skill identity. |
| Boundary clarity | Does the skill know when not to fire? | Anti-conditions, misuse checks, should-not-trigger scenarios. |
| Coverage fit | Does the visible output cover the book's useful value? | Coverage readiness, skill/workflow routing, source-value routes. |
| Context application safety | Does application context help without rewriting the source? | Application calibration, current-fact checks, source pollution checks. |
| Evidence confidence | What kind of proof supports the claim? | Internal review, scenario checks, same-book comparison, blind review, real-user evidence. |

## Evidence Confidence Levels

| Level | Meaning | Claim allowed |
| --- | --- | --- |
| Internal artifact review | Project team reviewed generated artifacts. | Internal quality signal. |
| Internal scenario check | Synthetic or scripted scenarios passed. | Regression and pressure evidence. |
| Same-book reference comparison | KiU compared against a separate reference on the same book where possible. | Comparative signal, not final preference proof. |
| External blind review | Outside reviewer chooses without attribution leakage. | External preference evidence. |
| Real-user validation | Real users apply skills in real decisions. | Usage-value evidence. |
| Domain-expert review | Qualified expert reviews source fidelity and action safety. | Expert confidence evidence. |

## Reading A Scorecard

A high score means the current evidence supports the claim at the stated evidence level. It does not automatically upgrade internal evidence into external validation.

For example, a score of `94` under internal artifact review means the generated artifact reads strongly to the project team. It does not mean real users prefer it until real-user or external blind evidence exists.

## Relationship To The v0.8 Architecture

| v0.8 step | User-facing dimensions most affected |
| --- | --- |
| 读准原书 | Source trust, evidence confidence. |
| 提炼判断 | Action helpfulness, coverage fit. |
| 生成技能 | Action helpfulness, boundary clarity. |
| 分流流程 | Boundary clarity, coverage fit. |
| 校准应用 | Context application safety, source trust. |
| 验证价值 | Evidence confidence, action helpfulness. |

## Claim Discipline

- Internal review can justify continued development and release readiness.
- Internal review cannot claim real-user success.
- Scenario checks can catch regressions and misuse risks.
- Scenario checks cannot replace external blind review.
- Same-book reference comparisons can reveal relative strengths and gaps.
- Same-book reference comparisons cannot prove general superiority.

# Scorecard: Financial Statement

Evidence level: internal artifact review and internal user-perspective review. This is not external blind review, real-user validation, or domain-expert validation.

## Summary

| Metric | Value |
| --- | ---: |
| Source | 88.1 |
| Generated | 92.9 |
| Usage | 98.6 |
| Practical effect | 98.6 |
| Overall | 93.2 |
| Release gate | PASS |
| C-class action value | 90 |
| User-facing overall | 90 |

## User-Facing Dimensions

| Dimension | Score |
| --- | ---: |
| source_trust | 90 |
| action_helpfulness | 91 |
| boundary_clarity | 92 |
| coverage_fit | 86 |
| context_application_safety | 89 |
| evidence_confidence | internal_user_perspective |

## Published Skills

| Skill | User-facing score | Reading |
| --- | ---: | --- |
| `accounting-quality-signal-check` | 91 | Accounting-quality risk gate for valuation decisions, with apply/defer/do_not_apply output and evidence checks. |
| `business-value-anchor-check` | 90 | Business-value anchoring skill that asks for decision goal, scope, constraints, and disconfirming evidence. |
| `workflow-gateway` | 81 | Thin workflow router, not a thick judgment skill. |

## Caveat

Financial Statement now passes the user-facing coverage gate, but it is still not a claim of complete financial-analysis domain coverage.

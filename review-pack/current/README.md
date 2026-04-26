# KiU Current Review Pack

This directory contains the current reviewer-facing source and artifact pack for KiU / 学以致用.

It is intentionally `current` only: the repository keeps one visible latest review pack, and historical versions are available through Git history rather than through separate versioned directories.

## Purpose

External reviewers can inspect the current source materials, generated skills, workflow routing artifacts, and score evidence without rerunning the KiU pipeline.

This pack is for artifact review. It does not claim external blind preference, real-user validation, domain-expert validation, or legal redistribution review.

## Contents

| Book | Sources | Published skills | Workflow candidates | Primary score file |
| --- | ---: | ---: | ---: | --- |
| Financial Statement | 1 | 3 | 5 | [scorecard](books/financial-statement/scorecard.md) |
| Effective Requirements | 1 | 3 | 12 | [scorecard](books/effective-requirements/scorecard.md) |
| Mao Anthology | 230 | 6 | 8 | [scorecard](books/mao-anthology/scorecard.md) |
| Poor Charlie | 5 | 6 | 0 | [scorecard](books/poor-charlie/scorecard.md) |
| Shiji | 130 | 3 | 0 | [scorecard](books/shiji/scorecard.md) |

Each book directory uses the same layout when material exists:

```text
books/<book>/
  source-card.md
  scorecard.md
  sources/
  generated-skills/
  workflow-candidates/
  routed-source-values/
  reports/
```

## Review Path

1. Read `source-card.md` for the book and run provenance.
2. Read `generated-skills/*/SKILL.md` for the user-facing skill artifacts.
3. Inspect `workflow-candidates/` and `routed-source-values/` when present to verify that non-skill material was not silently published as a skill.
4. Read `scorecard.md` for the current internal quality reading.
5. Use `reports/` only when deeper machine-readable evidence is needed.

## Evidence Boundary

The scorecards are internal review evidence. They support artifact review and release readiness, but they are not a substitute for external blind review, real-user validation, or domain-expert validation.

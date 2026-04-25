# Blind Review How-To

v0.6.8 supports three explicit reference-source modes. External projects remain reference or benchmark inputs only; they are never hidden upstream generators for KiU production artifacts.

## Reference Source Modes

- `internal-mock`: use KiU's explicit control-style benchmark pack. This is suitable for infrastructure and A/B pack smoke tests, but it is not an upstream project result.
- `upstream-cangjie`: use the vendored `.references/cangjie-skill/` checkout as explicit reference material. If the vendored checkout is absent, the command fails instead of silently falling back.
- `none`: run KiU-only checks without a comparison artifact.

## Smoke Commands

```bash
python scripts/run_blind_review.py --reference-source internal-mock
python scripts/run_blind_review.py --reference-source upstream-cangjie
python scripts/run_blind_review.py --reference-source none
```

## Boundary Coverage Gate

```bash
python scripts/audit_boundary_coverage.py \
  --review-cases tests/fixtures/v067-blind-review-cases.yaml \
  --review-pack reports/blind-review-packs/v0.6.7-multimodel-clean/clean-pack.json \
  --output reports/v0.6.8-boundary-coverage.md \
  --min-coverage 0.85
```

The CI gate writes the same audit to `/tmp` so pull requests do not modify committed reports.

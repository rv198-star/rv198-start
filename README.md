# KiU

KiU v0.1 is a graph-first, evidence-backed skill bundle format with a complete reference bundle and a local validator.

Start here:

- [Usage Guide](docs/usage-guide.md)
- [KiU Skill Spec v0.1](docs/kiu-skill-spec-v0.1.md)
- [KiU v0.2 Candidate Pipeline](docs/kiu-v0.2-pipeline.md)
- [Reference Bundle](bundles/poor-charlies-almanack-v0.1/manifest.yaml)

Validate locally:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
```

Build v0.2 refinement-scheduled candidate bundles:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id phase2-smoke
```

Generate deterministic seed bundles only:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

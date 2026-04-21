# KiU

[![CI](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml/badge.svg)](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml)

KiU v0.1 is a graph-first, evidence-backed skill bundle format with a complete reference bundle and a local validator.

Start here:

- [Usage Guide](docs/usage-guide.md)
- [KiU Skill Spec v0.1](docs/kiu-skill-spec-v0.1.md)
- [KiU Skill Spec v0.3](docs/kiu-skill-spec-v0.3.md)
- [KiU v0.2 Candidate Pipeline](docs/kiu-v0.2-pipeline.md)
- [Reference Bundle](bundles/poor-charlies-almanack-v0.1/manifest.yaml)

Validate locally:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
```

Build a refinement-scheduled candidate bundle:

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

Run one `llm-assisted` drafting pass with a mock provider:

```bash
KIU_LLM_PROVIDER=mock \
KIU_LLM_MOCK_RESPONSE="Replace me with a dense rationale.[^anchor:demo] [^trace:canonical/demo.yaml]" \
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id phase3-llm \
  --drafting-mode llm-assisted \
  --llm-budget-tokens 4000
```

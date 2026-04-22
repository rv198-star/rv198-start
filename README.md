# KiU

[![CI](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml/badge.svg)](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml)

KiU v0.1 is a graph-first, evidence-backed skill bundle format with a complete reference bundle and a local validator.

Start here:

- [Usage Guide](docs/usage-guide.md)
- [KiU Skill Spec v0.1](docs/kiu-skill-spec-v0.1.md)
- [KiU Skill Spec v0.3](docs/kiu-skill-spec-v0.3.md)
- [KiU v0.2 Candidate Pipeline](docs/kiu-v0.2-pipeline.md)
- [Reference Bundle](bundles/poor-charlies-almanack-v0.1/manifest.yaml)

Install locally:

```bash
python3 -m pip install -e .
```

Validate locally:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
```

If validation returns an error such as
`circle-of-competence: rationale_below_density_threshold (...)`,
the published skill text is below the domain profile's hard density floor and must be revised before release.

Build a refinement-scheduled candidate bundle:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase2-smoke
```

By default, pipeline output is written outside the repo to `/tmp/kiu-local-artifacts/generated/`.
Set `KIU_LOCAL_OUTPUT_ROOT=/your/path` to override the fixed local root, or pass
`--output-root` if you intentionally want another location such as `generated/`.

Generate deterministic seed bundles only:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

Run one `llm-assisted` drafting pass with a mock provider:

```bash
KIU_LLM_PROVIDER=mock \
KIU_LLM_MOCK_RESPONSE="Replace me with a dense rationale.[^anchor:demo] [^trace:canonical/demo.yaml]" \
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase3-llm \
  --drafting-mode llm-assisted \
  --llm-budget-tokens 4000
```

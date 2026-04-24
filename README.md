# KiU

[![CI](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml/badge.svg)](https://github.com/rv198-star/rv198-start/actions/workflows/ci.yml)

KiU v0.1 is a graph-first, evidence-backed skill bundle format with a complete reference bundle and a local validator.

Current release framing:

- `v0.5.0` closes the foundation line: multi-domain validation, cross-bundle graph merge, workflow-vs-agentic boundary enforcement, and three-layer review evidence.
- `v0.5.1` closes the corrective `cangjie-skill` gap-closure line: fresh same-source evidence shows a small but explicit usage lead without workflow-boundary drift.
- `v0.6.0` closes the source/provenance and Graphify-core bottom layer: raw-book ingestion, extraction audit records, provenance-rich graph materialization, tri-state graph effectiveness, graph navigation reports, generated usage smoke reviews, and final same-source evidence that preserves the `workflow_script` / `llm_agentic` boundary.
- `v0.6.0` does not claim a large final-usage lead over `cangjie-skill`; it proves the stronger evidence bottom layer is ready for the next graph-to-skill distillation step.
- `v0.7` is reserved for `In Use world-alignment` after the `v0.6.0` source/provenance line.

Start here:

- [Usage Guide](docs/usage-guide.md)
- [Backlog Board](backlog/board.yaml)
- [Version Roadmap Realignment](docs/2026-04-24-version-roadmap-v051-v06-v07.md)
- [KiU Skill Spec v0.1](docs/kiu-skill-spec-v0.1.md)
- [KiU Skill Spec v0.3](docs/kiu-skill-spec-v0.3.md)
- [KiU Skill Spec v0.4](docs/kiu-skill-spec-v0.4.md)
- [KiU Skill Spec v0.6](docs/kiu-skill-spec-v0.6.md)
- [v0.6 Final Evidence Pack](reports/2026-04-24-v0.6.0-final-release-evidence-pack.md)
- [v0.4.1 Assessment and v0.4.2 Plan](docs/2026-04-22-v0.4.1-assessment-and-v0.4.2-plan.md)
- [v0.5 Workflow Boundary Hardening Plan](docs/superpowers/plans/2026-04-22-v0.5-workflow-boundary-hardening.md)
- [v0.5 Workflow Delivery And Three-Layer Scoring Plan](docs/superpowers/plans/2026-04-22-v0.5-workflow-delivery-and-three-layer-scoring.md)
- [KiU v0.2 Candidate Pipeline](docs/kiu-v0.2-pipeline.md)
- [Reference Bundle](bundles/poor-charlies-almanack-v0.1/manifest.yaml)
- [Engineering Reference Bundle](bundles/engineering-postmortem-v0.1/manifest.yaml)

Install locally:

```bash
python3 -m pip install -e .
```

Validate locally:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_backlog.py --version v0.6.0
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

Review a generated run across source bundle, generated bundle, and usage outputs:

```bash
python3 scripts/review_generated_run.py \
  --run-root /tmp/kiu-local-artifacts/generated/poor-charlies-almanack-v0.1/phase2-smoke \
  --source-bundle bundles/poor-charlies-almanack-v0.1
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

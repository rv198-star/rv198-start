# Changelog

## Unreleased

### Added
- `llm-assisted` drafting now performs real `Rationale` generation with prompt templates, provider abstraction, validator precheck, rejection logging, and token-budget tracking.
- `reports/rounds/*.json` now records auditable LLM prompt/response artifacts for drafting rounds.
- `scripts/show_profile.py` prints the fully resolved domain profile for one bundle.
- GitHub Actions CI now runs the unit test suite plus reference-bundle validation.
- `docs/kiu-skill-spec-v0.3.md` publishes the v0.3 public spec surface.
- `workflow_candidates/examples/dcf-basic-valuation/steps.yaml` provides a schema-first workflow artifact example.
- `docs/CONTRIBUTING.md` defines the current i18n and verification rules.

### Changed
- Renamed scheduler config from `autonomous_refiner` to `refinement_scheduler`.
- Kept backward-compatible YAML alias loading for legacy `autonomous_refiner` bundles, with a deprecation warning during profile resolution.
- Published skills now enforce domain-profile minimum evaluation counts (`20/20/10` for investing).
- Reference skill eval summaries now report shared-corpus full-release coverage while keeping representative sample case lists.
- Repo docs now use portable `python3` commands instead of machine-local interpreter paths.

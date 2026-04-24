# Changelog

## Unreleased

### Added
- Added generated-run pipeline provenance so reports distinguish `raw_book_no_seed_cold_start` from `source_bundle_regeneration`.
- Added multi-file markdown directory ingestion with per-file source coordinate preservation through source chunks, graph materialization, and scaffolded bundles.
- Added v0.6.3 cold-start production gate planning and backlog tickets `KIU-672` through `KIU-675`.
- Added v0.6.4 borrowed-value maximization for biography/history/case/argument-heavy sources, including source-shape classification, `case_mechanism`, `situation_strategy_pattern`, and explicit transfer/anti-condition contracts.
- Added dual-sample regression evidence for Shiji and Mao anthology raw markdown cold-start runs in `reports/2026-04-24-v0.6.4-borrowed-value-evidence.md`.

### Changed
- Reference benchmark scorecards now expose `book_to_skill_cold_start_proven` instead of allowing stage-presence evidence to imply cold-start proof.
- Repeated collection boilerplate headings such as author names are filtered before chunking so they cannot become false skill/workflow candidates.
- v0.7 world-alignment planning is now explicitly gated on closing the v0.6.x cold-start production boundary.
- Borrowed-value judgment skills now reject pure summary, translation, fact lookup, biography intro, author-position query, and stance commentary as triggers while preserving the underlying evidence in the graph/source layer.
- Seed ranking now carries source-derived `agentic_priority`, so transferable mechanism skills are not buried behind high-support workflow or chapter-title candidates.
- Degenerate pure numeral/chapter IDs are filtered out of publishable candidate IDs during seed mining.
- v0.6.4 source hygiene now excludes navigation markdown from directory ingestion, reports real directory `source_file_count`, and ignores pure-number headings as semantic section anchors.
- Source review now scores `source_structure_quality` for raw-book bundles and counts consumed `INFERRED` mechanism nodes in tri-state effectiveness, so mechanism evidence packs are credited when they actually support generated skills.

### Verified
- Shiji raw markdown cold-start run: Source `90.0`, Generated `96.4`, Usage `95.8`, Overall `94.3`, release gate PASS; generated `historical-analogy-transfer-gate`, `historical-case-consequence-judgment`, and `role-boundary-before-action`.
- Mao anthology raw markdown cold-start run: Source `91.7`, Generated `93.2`, Usage `97.3`, Overall `94.0`, release gate PASS; generated `no-investigation-no-decision`, `principal-contradiction-focus`, and `historical-analogy-transfer-gate` as the first three judgment skills.
- v0.6.4 source ROI rerun: Shiji Source `94.0`, Generated `96.4`, Usage `95.8`, Overall `95.5`; Mao Source `93.0`, Generated `93.2`, Usage `97.5`, Overall `94.4`.

## [0.6.2] - 2026-04-24

### Added
- Effective Requirements generation now emits two judgment-heavy non-gateway skills, `solution-to-problem-reframing` and `stakeholder-resistance-tradeoff`, while preserving deterministic workflows under `workflow_candidates/`.
- `workflow-gateway` usage evidence now covers six routing and boundary cases instead of one happy-path smoke case.
- Generated-bundle preflight and three-layer review now report `workflow_gateway_boundary_preserved` and reject gateway skills that inline deterministic workflow checklist steps.

### Changed
- Bumped the package version to `0.6.2`.

### Verified
- Effective Requirements generated run: Source `96.7`, Generated `93.0`, Usage `98.9`, Overall `95.9`, release gate PASS.
- Effective Requirements output shape: `3` skills, `12` workflow candidates, `8` usage reviews, failure tags `{}`.
- Full regression: `154` unit tests pass; Poor Charlie and Engineering bundles validate as `VALID`.

## [0.6.1] - 2026-04-24

### Added
- Added graph-to-skill distillation contracts in generated `candidate.yaml` files, mapping `INFERRED` graph edges to bounded trigger expansion and `AMBIGUOUS` graph signals to edge-case boundary probes.
- Added benchmark scoring for `graph_to_skill_distillation_100` plus a v0.6.1 distillation gate that checks distillation score, workflow-boundary preservation, and same-scenario usage safety.
- Added a thin `workflow-gateway` skill when a generated run otherwise contains workflow candidates but zero installable skills; workflow logic remains under `workflow_candidates/`.
- Added `docs/kiu-skill-spec-v0.6.1.md` and `reports/2026-04-24-v0.6.1-distillation-evidence-pack.md`.

### Changed
- Generated `usage/scenarios.yaml` now receives graph-derived scenarios with `distillation_role`, `extraction_kind`, `source_location`, graph anchors, and concrete next-action language.
- Generated `SKILL.md` rendering now includes concise distillation notes only when tri-state graph signals are actually consumed, preserving seeded high-quality fixture content when no such signals exist.
- Reference benchmark markdown now surfaces the graph-to-skill distillation score and v0.6.1 gate status.

### Verified
- Poor Charlie generated run: Source `100.0`, Generated `97.8`, Usage `95.8`, Overall `97.9`, release gate PASS.
- Same-source benchmark: KiU usage `97.7` vs reference `96.4`, delta `+1.3`, weighted pass-rate parity `1.0`, usage winner `kiu`, failure tags `{}`.
- Distillation gate: `graph_to_skill_distillation_100 = 100.0`, `v061_distillation_gate.ready = true`, `3/3` inferred edges and `4/4` ambiguous signals consumed.
- Multi-sample regression: Poor Charlie `97.9`, Effective Requirements `91.8`, Financial Statement `93.6`, all release gates ready.
- v0.6 regression baseline: `7` checks executed, `7` passed, `0` failed.

## [0.6.0] - 2026-04-24

### Added
- Added the v0.6 raw-book source/provenance line: source chunks, book overview artifacts, extraction-result audit records, provenance-rich graph materialization, graph communities, and GRAPH_REPORT navigation output.
- Added generated usage smoke reviews to the default `build_candidates.py` path so generated bundles can be reviewed across source, generated, and usage layers without manual `/tmp` patching.
- Added final v0.6 release evidence covering three-layer production scores, same-source `cangjie-skill` benchmark results, and explicit Graphify-core absorption limits.

### Changed
- Tightened `invert-the-problem` boundary language for concept, definition, and historical-example queries; explanatory lookup prompts no longer count as live inversion decisions.
- Updated v0.6 release narrative from future reservation to delivered `In Use + provenance + workflow-boundary` release line.
- Bumped the package version to `0.6.0`.

### Verified
- Poor Charlie generated run: Source `100.0`, Generated `97.8`, Usage `95.8`, Overall `97.9`, release gate PASS.
- Same-source benchmark against local `poor-charlies-almanack-skill`: KiU usage `97.7` vs reference `96.4`, delta `+1.3`, weighted pass-rate parity at `1.0`, `usage_winner = kiu`, failure tags `{}`.
- Graphify core closure now scores `graphify_core_absorbed_100 = 100.0`: node/edge provenance, tri-state density, tri-state effectiveness, communities, and graph report ratios all reach `1.0` while same-source usage quality remains ahead of the reference pack.
- v0.6 regression baseline executed `7` checks with `7` pass / `0` fail across unit tests, investing/engineering validation, and generated-run review paths.

## [0.5.1] - 2026-04-24

### Added
- Added per-skill `usage/scenarios.yaml` for the five published investing skills so source bundles carry explicit trigger language, edge handling, and next-action shapes into generated bundles.
- Added a generated `value-assessment-source-note` parent skill for the margin family, plus dedicated evaluation cases under `evaluation/value-assessment/` and a new canonical trace `unused-pricing-power-signal.yaml`.
- Added version-roadmap and benchmark-gap archive docs clarifying the split between `v0.5.1`, reserved `v0.6`, and reserved `v0.7`.

### Changed
- Generated bundles now preserve scenario families in `Usage Summary` and inherit source `Revision Summary` content instead of regressing to generic seed text.
- The margin family now uses explicit parent/specialist topology: `value-assessment-source-note` handles value-anchor judgment first, then delegates sizing decisions to `margin-of-safety-sizing`.
- Reference benchmark concept alignment now prefers generated-run skill reviews when `--run-root` is provided, so same-source comparisons score the actual generated bundle instead of falling back to the published source bundle.
- Investing trigger registry was extended for valuation-parent routing, and additional candidates can now carry explicit source/scenario anchors.
- The `value-assessment-source-note` contract and usage language were sharpened around price-vs-value sequencing, unused pricing power, private-business edge handling, and explicit handoff conditions.

### Verified
- Release verification now shows stable same-source superiority against the local `poor-charlies-almanack-skill` reference pack: `usage_winner = kiu`, `average_usage_score_delta_100 = +1.0`, weighted pass-rate parity at `1.0`, and no failure tags in the fresh benchmark archive.

## [0.5.0] - 2026-04-22

### Added
- Added the second public domain profile `engineering` plus the reference source bundle `engineering-postmortem-v0.1`, including `postmortem-blameless`, `blast-radius-check`, and shared canonical traces/evaluation cases.
- Added cross-bundle graph merge support with `src/kiu_graph/merge.py`, `scripts/merge_graphs.py`, and validator `--merge-with` coverage for external relations.
- Added generated-run three-layer review scoring via `scripts/review_generated_run.py`, emitting `reports/three-layer-review.json` with auditable 100-point scores for source bundle, generated bundle, and usage outputs.
- Added minimum workflow deliverable skeletons for downgraded workflow candidates: `workflow.yaml` and `CHECKLIST.md` now ship under `workflow_candidates/<id>/`.

### Changed
- Hardened the workflow-vs-agentic boundary so `high/high` routing stays outside `bundle/skills/` while still preserving usable workflow preflight artifacts for audit and execution prep.
- `generate_candidates.py` and `build_candidates.py` now report workflow candidate counts from generated run metrics instead of silently under-reporting them in CLI summaries.
- Bundle validation now understands merged external bundle references and enforces the engineering-domain release path with the same structural rigor as investing.
- The v0.5 foundation line is now release-framed as: multi-domain validation, cross-bundle graph proof, explicit workflow/agentic boundary, and fresh three-layer review evidence.

## [0.4.2] - 2026-04-22

### Added
- `docs/kiu-skill-spec-v0.4.md` documents the v0.4 public surface: single-domain production-line hardening, workflow-vs-agentic routing, production quality gating, example fixtures, and honest rendered summaries.
- `docs/2026-04-22-v0.4.1-assessment-and-v0.4.2-plan.md` records the combined external review, local real-use findings, and the v0.4.2 / v0.5 split.

### Changed
- Generated candidate `SKILL.md` files now render `Evaluation Summary` from `eval/summary.yaml` and `Revision Summary` from `iterations/revisions.yaml`; refinement mutations refresh those sections instead of only bumping metadata.
- Generated-bundle preflight now rejects `Evaluation Summary` / `Revision Summary` drift against their structured YAML sources.
- `automation.yaml` profile resolution now accepts `inherits_from` as the preferred field while keeping `inherits` as a compatibility alias.
- The financial-statement example fixture now routes story-only valuation cases into `lock-onto-accounting-value` instead of excluding the exact adversarial pattern it should catch.
- Published investing skill revision notes now label the v0.4 content rewrite as a manual content upgrade rather than implying a loop-driven refinement run.

## [0.4.1] - 2026-04-22

### Added
- Example-fixture source bundles can now be scaffolded from repo fixture YAML plus compact source docs without writing generated artifacts back into the repository.
- Fixed local artifact roots under `/tmp/kiu-local-artifacts/` became the default output surface for generated bundles and scaffolded fixture sources.

### Changed
- Fixture packaging and local-output handling were hardened so v0.4 smoke bundles can be generated, inspected, and discarded without polluting git state.

## [0.4.0] - 2026-04-22

### Added
- Five published investing skills were rewritten to the v0.4 content standard with denser rationale, explicit three-trace evidence summaries, richer relation links, and revision `4`.
- Canonical trace coverage for the reference investing bundle expanded from `3` traces to `15`.
- Production quality gating now scores generated bundles with `artifact_quality`, `production_quality`, and a bundle-level grade driven by domain profile thresholds.
- Example fixtures for `effective-requirements-analysis` and `financial-statement-analysis` were added as second-line source-bundle smoke tests.

### Changed
- Reference-skill evaluation summaries now bind to full shared-corpus coverage while keeping representative case references.
- Generated candidate runs now emit release-quality reports instead of only structural bundle artifacts.

## [0.3.1] - 2026-04-22

### Added
- Published-skill density can now be enforced as a hard domain gate through profile-driven `content_density.published_requirement`.
- Validator errors now expose empty or missing shared-corpus glob expansion in generated and published evaluation bindings.

### Changed
- `_resolve_subset_cases` now expands glob case references before counting totals, rejects zero-match globs, and enforces exact `total == len(resolved_cases)` consistency.
- Investing-domain published bundles now require hard density gating at `240` rationale characters plus anchor coverage instead of warning-only behavior.
- Bundle automation profile metadata moved to `kiu.pipeline-profile/v0.3`, and empty trigger registries now surface an explicit warning.

## [0.3.0] - 2026-04-21

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

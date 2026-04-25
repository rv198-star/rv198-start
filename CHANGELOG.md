# Changelog

## Unreleased


## [0.7.0] - 2026-04-25

### Added
- Added the `学以致用` world-alignment foundation line as isolated enhancement rather than fusion rewrite.
- Added offline world-context artifacts under `world_alignment/`, including context, review, and usage outputs without mutating source-faithful `SKILL.md` artifacts.
- Added world-alignment need scoring, intervention levels, relevance arbitration, no-forced-enhancement policy, source-fit review, dilution-risk review, and no-web hallucination risk checks.
- Added proxy usage generation and same-book cangjie reference benchmark evidence for v0.7.0 foundation evaluation.

### Changed
- Reframed external blind/user validation as future condition-dependent validation rather than a short-term v0.7.0 release blocker.
- Updated project guidance to require staged verification feedback for long-running full checks.

### Verified
- World alignment focused tests: `16` passed.
- World alignment, proxy usage, and reference benchmark tests: `40` passed.
- Version-related regression subset: `112` passed.
- Full unittest regression: `216` passed.
- `backlog/board.yaml` parsed successfully.

### Limits
- v0.7.0 does not claim live web factual validation, multi-world or multi-stance modeling, real external blind-review closure, or real-user usage validation.
- World alignment is a gated offline pressure layer; it may enrich or caveat application, but must not silently rewrite the source-derived skill.

## [0.6.8] - 2026-04-25

### Fixed
- Upgraded generated boundary rendering for v0.6.7 blind-review weak spots by exposing enum-style `do_not_fire_when` signals for character evaluation, viewpoint summary, fact lookup, translation, workflow-template requests, single-anecdote overreach, and surface-similarity misuse.
- Added consequence-skill scenario families for positive, edge, and refusal cases, including short-gain/long-cost stress testing and workflow/template refusal paths.
- Redacted the v0.6.7 blind-review control pack from `cangjie-protocol` naming to `control-style-B`, keeping external references explicit in benchmark/evidence docs while removing attribution leakage from reviewer-facing packs.

### Added
- Added `scripts/audit_boundary_coverage.py`, `tests/fixtures/v067-blind-review-cases.yaml`, and CI coverage audit for the fixed 26-case v0.6.7 blind-review fixture.
- Added `scripts/run_blind_review.py` with `--reference-source=internal-mock|upstream-cangjie|none` to make reference-source selection explicit rather than implicit.
- Added role-boundary robustness proxy checks and `reports/v0.6.8-role-boundary-robustness.md` for six prompt-style variants.
- Added the public v0.6.8 Shiji control-style-B blind review pack under `reports/blind-review-packs/v0.6.8-shiji-control-style-B/` without committing the private unblind key.
- Added `docs/blind-review-howto.md`, `reports/v0.6.8-boundary-coverage.md`, and `reports/2026-04-25-v0.6.8-final-closure-evidence.md`.

### Verified
- Boundary coverage audit: `26/26` cases covered, coverage ratio `1.0000` against the fixed v0.6.7 blind-review fixture.
- v0.6 regression baseline replay: `7` checks executed, `7` passed, `0` failed; repository unittest baseline reports `196` tests passing in that replay.
- v0.6.8 Shiji blind pack: `26` pairs, `placeholder_count=0`, hidden role balance `13/13`.
- Reference-source smoke: `internal-mock`, `upstream-cangjie`, and `none` all return ready.
- Evidence honesty retained: same-scenario heuristic benchmark reports KiU `85.5` vs control-style-B `88.2` (`-2.7`), so external blind closure remains a v0.7 gate rather than a v0.6.8 claim.

### Sealed
- v0.6.x is sealed at v0.6.8. Follow-up work moves to v0.7, starting with real external blind review and architecture-level world-alignment planning.

## [0.6.7] - 2026-04-25

### Fixed
- Reran Shiji and Mao raw-book no-seed closure generation with the upgraded borrowed-value anti-condition contracts so the new boundaries are present in generated `SKILL.md` artifacts, not only in unit-level contract builders.
- Fixed blind review excerpts to front-load boundary and anti-misuse evidence before long contract/method/rationale text, preventing reviewer-visible packs from hiding `do_not_fire_when` and `anti_conditions` behind truncation.
- Added end-to-end same-scenario decoy validation for KIU-685: p010/p020/p023-style character-evaluation, workflow-template, and viewpoint-summary prompts must be scored as explicit no-fire boundary matches.

### Added
- Added corrected v0.6.7 Shiji blind review pack under `reports/blind-review-packs/v0.6.7-shiji-control-style-B/`.
- Added `reports/2026-04-25-v0.6.7-boundary-rendering-and-decoy-evidence.md`.

### Verified
- v0.6.7 Shiji blind pack: `26` pairs, `placeholder_count=0`, hidden A/B role balance `13/13`.
- Reviewer-visible `option_b` decoy check: at least `3` should-not-trigger pairs contain the new anti-condition text.
- v0.6 compatibility baseline: `7` checks executed, `7` passed, `0` failed.
- Same-source benchmark keeps external blind closure pending: `external_blind_100=0.0`, `closure_100=0.0`.

## [0.6.6] - 2026-04-25

### Fixed
- Fixed blind review pack artifact resolution for generated KiU bundles by reading `bundle/skills/<skill_id>/SKILL.md`; reviewer packs now report `placeholder_count` and the v0.6.6 Shiji pack has `0` placeholders.
- Fixed blind review A/B assignment by using deterministic balanced hidden roles; the v0.6.6 Shiji pack is balanced at `13/13`.
- Extended borrowed-value anti-misuse boundaries to reject character-evaluation, viewpoint-summary, and mechanical workflow-template prompts.
- Added `case_density_score` to source routing and seed scoring so mechanism-dense chapters outrank weak source forms such as divination lists, tables, and genealogy-like material.
- Added rationale template collision detection to generated-run review so repeated generic I/Rationale text becomes an explicit quality warning.
- Added `--compatibility-regression-report` support to reference benchmarks; v0.6.6 replayed the v0.6 baseline with `7/7` checks passing and reports `compatibility_regression_risk = pass`.

### Added
- Added corrected v0.6.6 Shiji blind review pack under `reports/blind-review-packs/v0.6.6-shiji-cangjie-protocol/`.
- Added `reports/2026-04-25-v0.6.6-blind-review-pack-fix-evidence.md`.

### Verified
- Targeted review-fix verification: `25` tests pass for blind pack, v0.6.6 review fixes, and reference benchmark compatibility.
- Full regression: `190` tests pass.
- v0.6 compatibility baseline: `7` checks executed, `7` passed, `0` failed.

## [0.6.5] - 2026-04-25

### Added
- Added cangjie core closure artifacts: raw-book runs now emit `reports/ria-tv-stage-report.json` with RIA-TV++ stage visibility, extractor responsibilities, triple-verification stage status, distillation status, linking status, and pressure-test stage status.
- Added chapter-title pseudo-skill hygiene before candidate promotion plus `reports/pseudo-skill-audit.json` so rejected headings and routed workflow candidates are auditable rather than silently deleted.
- Added split cangjie methodology scoring with `cangjie_methodology_internal_100`, `cangjie_methodology_external_blind_100`, `cangjie_methodology_closure_100`, `cangjie_methodology_gate`, and layered `final_artifact_effect` scoring so same-scenario usage wins cannot be misreported as cangjie methodology closure.
- Added RIA-TV++ and triple-verification artifact ingestion to Layer 2 scoring, with internal methodology separated from external blind-preference closure evidence.
- Added `cangjie_core_baseline_matrix` to reference benchmark JSON/Markdown/CLI output so each cangjie capability reports pass/weak/missing status.
- Added per-skill `ria_tv_provenance` and structured `distillation_contract` metadata for generated thick skills.
- Added generated `reports/pressure-tests.json` decoy pressure packs and pressure summary ingestion for Layer 2 scoring.
- Added the optional anonymous `schemas/blind-preference-review-v0.1.json` evidence interface plus blind summary ingestion for Layer 2 scoring.
- Added release-threshold same-source scenario packs for the benchmark-only cangjie protocol baseline, covering trigger, boundary, decoy, and edge-case prompts.
- Added `scripts/build_blind_review_pack.py`, `scripts/merge_blind_review_response.py`, and the committed v0.6.5 Shiji reviewer pack under `reports/blind-review-packs/v0.6.5-shiji-cangjie-protocol/`.
- Added `reports/2026-04-25-v0.6.5-cangjie-core-closure-evidence.md` and the v0.6.5 implementation plan.

### Changed
- Generated candidate metadata now carries `ria_tv_distillation`, `ria_tv_provenance`, and `distillation_contract` without rewriting existing high-quality seeded rationale.
- Seed verification now exposes triple-verification dimensions and blocks weak non-workflow skill promotion when cross-evidence, predictive/action value, or uniqueness is below promotion thresholds.
- Reference benchmark CLI summaries now expose `final_artifact_effect_*`, `cangjie_methodology_*`, `cangjie_core_baseline_matrix_*`, and `compatibility_regression_risk`.
- Workflow-gateway candidates use `gateway_provenance` instead of thick-skill RIA-TV provenance, preserving the workflow/agentic boundary.

### Verified
- Batch 1 targeted verification: `5` tests pass for chapter-title filtering, pseudo-skill audit, and compatibility summary fields.
- Batch 2 targeted verification: `5` tests pass for RIA-TV++ stage artifacts, triple verification, distillation metadata, and existing Shiji/Mao-style cold-start smoke behavior.
- Batch 3 reference benchmark verification: `18` tests pass for methodology gate, pressure/blind evidence ingestion, two-layer effect reporting, and same-source scenario threshold coverage.
- Final regression: `183` tests pass after baseline matrix, per-skill provenance, promotion-gate, pressure-pack, blind-evidence loader, and same-source scenario expansion changes.
- Shiji same-source benchmark against the local benchmark-only cangjie protocol baseline: `26` scenarios across `2` matched pairs, KiU usage delta `+1.9`, weighted pass-rate delta `+0.1539`, cangjie core `99.2`, methodology internal `100.0`, external blind `0.0`, closure `0.0`.
- Cangjie core baseline matrix now reports only `blind_preference` as missing; `same_source_benchmark` clears the release threshold, the final artifact claim is `internal_depth_proven_external_blind_missing`, and the external review pack is ready for auditors.

## [0.6.4] - 2026-04-25

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
- v0.6.4 evidence now reports the full reference scorecard line: KiU foundation retained, Graphify core absorbed, and cangjie core absorbed.

### Verified
- Shiji raw markdown cold-start run: Source `90.0`, Generated `96.4`, Usage `95.8`, Overall `94.3`, release gate PASS; generated `historical-analogy-transfer-gate`, `historical-case-consequence-judgment`, and `role-boundary-before-action`.
- Mao anthology raw markdown cold-start run: Source `91.7`, Generated `93.2`, Usage `97.3`, Overall `94.0`, release gate PASS; generated `no-investigation-no-decision`, `principal-contradiction-focus`, and `historical-analogy-transfer-gate` as the first three judgment skills.
- v0.6.4 source ROI rerun: Shiji Source `94.0`, Generated `96.4`, Usage `95.8`, Overall `95.5`; Mao Source `93.0`, Generated `93.2`, Usage `97.5`, Overall `94.4`.
- Reference scorecard transparency: Shiji cold-start scorecard reports KiU foundation `99.8`, Graphify core `91.0`, cangjie core `64.2`; Mao reports KiU foundation `99.7`, Graphify core `89.5`, cangjie core `69.5`.

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

# KiU v0.1 Usage Guide

## Quick Start

KiU 目前包含两层内容：

- `v0.1`：graph-first、evidence-backed 的 reference bundle 与 validator
- `v0.2`：从已发布 graph snapshot 生成 candidate seeds，并默认执行 refinement scheduling
- `v0.3`：domain-profile 驱动的 validator / refinement scheduler / `llm-assisted` drafting

当前仓库内置的参考语料仍然是 *Poor Charlie's Almanack*。

Validate the bundle from the repo root:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
```

Expected result:

- the validator prints `VALID`
- the test suite reports all tests passing

Build a v0.2 refinement-scheduled candidate run:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id phase2-smoke
```

Generate deterministic seed output only:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

## What This Repo Contains

- one published bundle: `bundles/poor-charlies-almanack-v0.1/`
- five published P0 skills
- one published graph snapshot bound by `graph_hash`
- shared canonical traces
- shared evaluation corpus with:
  - `20` `real_decisions`
  - `20` `synthetic_adversarial`
  - `10` `out_of_distribution`
- validator code and acceptance tests
- one v0.2/v0.3 candidate pipeline with deterministic seed generation, refinement scheduling, `llm-assisted` rationale drafting, and generated-bundle preflight

## Repository Layout

```text
.
├── bundles/
│   └── poor-charlies-almanack-v0.1/
│       ├── manifest.yaml
│       ├── graph/graph.json
│       ├── skills/<skill-id>/
│       ├── traces/
│       ├── evaluation/
│       └── sources/
├── docs/
├── schemas/
├── scripts/
├── src/
├── generated/  # ignored local output
└── tests/
```

Key directories:

- `bundles/poor-charlies-almanack-v0.1/manifest.yaml`
  - bundle identity, graph binding, skill index, and shared-asset roots
- `bundles/poor-charlies-almanack-v0.1/graph/graph.json`
  - the published graph snapshot used as the bundle's graph source of truth
- `bundles/poor-charlies-almanack-v0.1/skills/`
  - thick skill views for humans and reviewers
- `bundles/poor-charlies-almanack-v0.1/traces/`
  - canonical usage traces shared across skills
- `bundles/poor-charlies-almanack-v0.1/evaluation/`
  - shared evaluation pool split into real, adversarial, and OOD subsets
- `schemas/`
  - public interface definitions for the bundle manifest, anchors, eval summaries, revisions, relation enum, and KiU Test
- `workflow_candidates/examples/`
  - schema-first examples for workflow script artifacts
- `scripts/generate_candidates.py`
  - v0.2 deterministic seed generator
- `scripts/build_candidates.py`
  - v0.2/v0.3 default unattended builder
- `scripts/show_profile.py`
  - prints the resolved domain profile for one bundle
- `generated/`
  - local v0.2 output root; intentionally not committed

## How To Read A Skill

Open any skill directory under `bundles/poor-charlies-almanack-v0.1/skills/<skill-id>/`.

Read files in this order:

1. `SKILL.md`
   - the human-facing thick spec
   - starts with `Identity` and `Contract`
   - ends with usage, evaluation, and revision summaries
2. `anchors.yaml`
   - proves double anchoring
   - binds the skill to graph objects and to resolvable source/scenario evidence
3. `eval/summary.yaml`
   - records KiU Test status and the current subset-level evaluation result
4. `iterations/revisions.yaml`
   - records what changed from one revision to the next and why

For a published skill, verify these minimum conditions:

- `status: published`
- `skill_revision` matches the manifest
- at least one graph anchor set exists
- at least one source or scenario anchor set exists
- at least three usage trace references appear in `Usage Summary`
- all three evaluation subsets report `status: pass`

## How To Validate The Bundle

Run the validator:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
```

The validator checks:

- manifest completeness
- graph hash consistency
- required skill files
- required `SKILL.md` sections
- allowed relation enum usage
- trigger registry coverage
- double anchoring rules
- domain-profile published minimum eval counts
- eval summary consistency
- revision-log consistency
- published-skill constraints:
  - at least 3 usage traces
  - all evaluation subsets pass
  - domain minimum eval counts
  - at least one revision cycle

For generated bundles, run the pipeline preflight through the test suite:

```bash
python3 -m unittest tests/test_pipeline.py
```

That check covers:

- generated candidate bundle rendering
- `candidate.yaml` presence
- metrics report emission
- rejection of `workflow_script_candidate` inside `bundle/skills/`
- unattended build terminal state emission

## How To Extend The Bundle

To add or revise a skill in this release shape:

1. Duplicate an existing skill directory as a starting point.
2. Write or update `SKILL.md` so all 8 required sections remain present.
3. Add `anchors.yaml` entries that include both:
   - graph anchors
   - source or scenario anchors
4. Update `eval/summary.yaml` with current KiU Test and subset results.
5. Append a new entry to `iterations/revisions.yaml`.
6. If the skill's rationale, boundary, anchors, or evaluation conclusion changes, bump `skill_revision`.
7. If the published graph snapshot changes, update:
   - `graph/graph.json`
   - `manifest.yaml`
   - any affected `anchors.yaml`
   - any affected `revisions.yaml`
8. Re-run validation and tests.

## Publishing Workflow

The current repo already includes the reference public release shape. For future releases, use this order:

1. update bundle content
2. validate locally
3. run acceptance tests
4. commit
5. publish or push

Recommended commands:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
git status --short
git add .
git commit -m "Describe the release change"
```

## How To Use The v0.2 Pipeline

v0.2 consumes an existing source bundle and its `automation.yaml`.

Run:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id phase2-smoke
```

If you only want the deterministic seed bundle:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

If you want the current `llm-assisted` surface, use:

```bash
KIU_LLM_PROVIDER=mock \
KIU_LLM_MOCK_RESPONSE="Dense rationale text with anchor refs.[^anchor:demo] [^trace:canonical/demo.yaml]" \
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id phase3-llm \
  --drafting-mode llm-assisted \
  --llm-budget-tokens 4000
```

Today the shipped LLM drafting surface is intentionally narrow:

- `Rationale` can be drafted by the provider layer
- validator precheck decides whether the draft is accepted
- rejected drafts are preserved in `reports/rounds/*.json`
- `Identity`, `Contract`, `Relations`, and anchors remain non-LLM-owned

## Workflow Script Artifact Example

KiU v0.3 also ships a schema-first workflow artifact example at:

- `workflow_candidates/examples/dcf-basic-valuation/steps.yaml`

This is the current reference shape for `workflow_script_candidate` delivery:

- YAML DSL only
- no execution engine implied
- intended for structure validation and review first

Read generated output in this order:

1. `generated/<bundle-id>/<run-id>/reports/metrics.json`
2. `generated/<bundle-id>/<run-id>/reports/scorecard.json`
3. `generated/<bundle-id>/<run-id>/reports/final-decision.json`
4. `generated/<bundle-id>/<run-id>/bundle/manifest.yaml`
5. one generated `bundle/skills/<skill-id>/`
6. if present, `workflow_candidates/<candidate-id>/candidate.yaml`

The most important v0.2 metadata is in `candidate.yaml`:

- `workflow_certainty`
- `context_certainty`
- `recommended_execution_mode`
- `disposition`
- `current_round`
- `terminal_state`
- `overall_quality`
- `net_positive_value`

Interpretation:

- `skill_candidate` means the seed remains in KiU candidate space
- `workflow_script_candidate` means the seed should be treated as deterministic workflow logic, not as a formal KiU skill candidate
- `ready_for_review` means the refinement-scheduler loop reached its quality threshold
- `do_not_publish` means the refinement-scheduler loop found insufficient 净新增价值
- `max_rounds_reached` means the loop hit its round cap before converging

## Design Rationale

### 1. Graph-first, not graph-only

The graph snapshot is the bundle's formal evidence substrate, but not the final product. KiU does not ship a graph browser and call it done. It ships skills that can be reviewed, revised, and validated against that graph.

### 2. Thick skills instead of thin contracts

`SKILL.md` is intentionally thicker than a dispatch-only config file. The contract has to stay machine-tractable, but reviewers also need rationale, evidence summary, usage summary, evaluation summary, and revision history in one place.

### 3. Double anchoring is non-negotiable

Graph anchors alone are too abstract. Source anchors alone are too local and do not guarantee structural consistency. Requiring both makes each published skill simultaneously:

- structurally attached to the released graph snapshot
- textually attached to concrete evidence

### 4. Shared traces and evaluation pools reduce duplication

Traces and eval cases live at the bundle level because they are canonical assets, not per-skill copies. A single case can support multiple skills, and future bundle revisions can expand the pool without scattering duplicate files.

### 5. Revision logs are first-class

KiU is designed for looped refinement rather than one-shot distillation. `iterations/revisions.yaml` is therefore part of the core spec, not an afterthought. A published skill without a visible revision trail is hard to trust.

### 6. v0.1 is spec-first on purpose

This release does not try to solve extraction automation, runtime dispatch, or MCP integration. It establishes:

- the release unit
- the mandatory files
- the public schemas
- the validator behavior
- the content shape of a complete reference bundle

That keeps the first release falsifiable and small enough to review.

### 7. v0.2 adds candidate generation, not automatic publication

The pipeline exists to reduce drafting overhead while preserving evidence discipline. It is intentionally constrained:

- graph snapshot is still the upstream truth
- generated output is still only `under_evaluation` or `ready_for_review`
- `high/high` workflow-context certainty is routed away from KiU skill publication
- refinement scheduling is the default
- human review remains an optional gate before publication

## Recommended Reading Order

If someone is new to the project, this order works well:

1. `docs/kiu-skill-spec-v0.1.md`
2. `docs/usage-guide.md`
3. `docs/kiu-v0.2-pipeline.md`
4. `bundles/poor-charlies-almanack-v0.1/manifest.yaml`
5. one published skill directory
6. `src/kiu_validator/core.py`
7. `tests/test_validator.py`

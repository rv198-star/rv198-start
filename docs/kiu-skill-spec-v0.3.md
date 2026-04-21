# KiU Skill Spec v0.3

KiU v0.3 keeps the v0.1 graph-first bundle shape and the v0.2 candidate pipeline, but upgrades the release contract around three themes:

- `Knowledge Density`: a skill must not only be structurally complete, it must carry reusable judgment content.
- `Domain Profiles`: validation and refinement behavior is inherited from `shared_profiles/<domain>/`.
- `Honest Refinement`: `refinement_scheduler` owns round tracking and gating; `llm-assisted` drafting is a separate, auditable content-writing surface.

## Bundle Shape

The published bundle layout remains graph-first:

```text
bundle/
├── manifest.yaml
├── automation.yaml
├── graph/graph.json
├── skills/<skill-id>/
│   ├── SKILL.md
│   ├── anchors.yaml
│   ├── eval/summary.yaml
│   └── iterations/revisions.yaml
├── traces/
├── evaluation/
└── sources/
```

`manifest.yaml` must include `domain`, and `automation.yaml` is now expected to inherit from a domain profile.

## Domain Profile Model

Every bundle resolves its runtime policy from:

1. `shared_profiles/default/profile.yaml`
2. `shared_profiles/<domain>/profile.yaml`
3. bundle-local `automation.yaml` overrides

The resolved profile can carry:

- `trigger_registry`
- `content_density`
- `min_eval_cases_for_published`
- `refinement_scheduler`

Legacy `autonomous_refiner` is still readable as an alias, but v0.3 treats it as deprecated.

## Trigger Registry

All trigger-like symbols used by a skill must resolve through the domain trigger registry.

Covered fields:

- `Contract.trigger.patterns`
- `Contract.trigger.exclusions`
- `Contract.boundary.fails_when`
- `Contract.boundary.do_not_fire_when`

Each trigger entry must include:

- `symbol`
- `definition`
- `positive_examples`
- `negative_examples`

Unknown symbols are validator errors. Empty definitions or missing examples are validator warnings.

## Content Density

v0.3 introduces warning-level density checks so a skill cannot pass purely on structure.

The validator checks:

- `Rationale` character density
- `Rationale` anchor reference count
- `Evidence Summary` anchor reference count

Anchor references use KiU footnote-style markers such as:

- `[^anchor:circle-source-note]`
- `[^trace:canonical/dotcom-refusal.yaml]`

Density failures warn in v0.3 and are designed to become harder gates in later versions.

## Published Skill Gates

For `status: published`, v0.3 requires all of the following:

- double anchoring remains valid
- all three evaluation subsets report `status: pass`
- subset counts meet the domain profile minimums
- at least one revision cycle has occurred
- at least three usage trace references remain attached

The default investing profile requires:

- `real_decisions >= 20`
- `synthetic_adversarial >= 20`
- `out_of_distribution >= 10`

## Refinement Scheduler

`refinement_scheduler` is the honest name for the deterministic loop controller that:

- tracks rounds
- applies mutation plans
- scores candidates against bundle baselines
- emits terminal states
- writes round reports and final decisions

It does not, by itself, imply content generation.

## LLM-Assisted Drafting

`--drafting-mode llm-assisted` is a real v0.3 execution path.

Current shipped surface:

- `Rationale` drafting

Required behavior:

- prompt templates are versioned under `src/kiu_pipeline/refiner/prompts/`
- provider selection is abstracted behind a provider layer
- outputs go through generated-bundle validator precheck before acceptance
- rejected drafts are recorded in `reports/rounds/*.json`
- token budget usage is tracked per run

`Identity`, `Contract`, `Relations`, and `anchors.yaml` remain non-LLM-owned surfaces.

## Validator Expectations

The v0.3 validator now checks:

- bundle completeness
- graph hash binding
- trigger registry coverage
- relation target existence
- double anchors
- density warnings
- published minimum eval counts
- published revision-loop requirement
- generated candidate preflight requirements

It must also remain forward-compatible with legacy v0.2-style bundle profiles that still use `autonomous_refiner`.

## Tooling Surface

v0.3 expects these public tools to exist:

- `scripts/validate_bundle.py`
- `scripts/build_candidates.py`
- `scripts/generate_candidates.py`
- `scripts/show_profile.py`

CI should run unit tests and validate the reference bundle on every push and pull request.

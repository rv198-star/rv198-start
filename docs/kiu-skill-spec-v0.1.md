# KiU Skill Spec v0.1

KiU v0.1 defines a graph-first bundle format for evidence-backed, executable skills. The graph snapshot is the published source of truth. `skills/` exposes thick human-reviewable views anchored to that same graph snapshot and to resolvable source or scenario evidence.

## Bundle Layout

```text
bundle/
├── manifest.yaml
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

## Required SKILL.md Blocks

Every skill directory must provide these sections in order:

1. `Identity`
2. `Contract`
3. `Rationale`
4. `Evidence Summary`
5. `Relations`
6. `Usage Summary`
7. `Evaluation Summary`
8. `Revision Summary`

## Double Anchoring

Active skills (`under_evaluation` or `published`) require both anchor layers:

- Graph anchors: resolvable `node_ids`, `edge_ids`, or `community_ids` against `graph/graph.json`
- Source or scenario anchors: resolvable file paths plus location spans that point to evidence snippets, usage traces, or evaluation cases

Missing either layer blocks publication.

## Versioning

- `bundle_version`: release version for the whole bundle
- `skill_revision`: local revision number for one skill within the bundle
- `graph_hash`: immutable binding to the current graph snapshot

If the graph changes in a way that affects a skill's anchors, boundary, rationale, or evaluation conclusion, the skill must bump `skill_revision`.

## KiU Test Interface

KiU v0.1 standardizes three structural gates and three shared evaluation subsets:

- `Trigger Test`
- `Fire Test`
- `Boundary Test`
- `real_decisions`
- `synthetic_adversarial`
- `out_of_distribution`

## Reference Implementation

This workspace includes:

- `schemas/`: public schema and interface files
- `bundles/poor-charlies-almanack-v0.1/`: reference bundle for the five P0 skills
- `scripts/validate_bundle.py`: validator CLI
- `tests/test_validator.py`: acceptance tests for the reference bundle

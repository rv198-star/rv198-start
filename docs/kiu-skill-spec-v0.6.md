# KiU Skill Spec v0.6

## Positioning

`v0.6` does not replace the `v0.5` foundation. It extends the upstream half of the
pipeline so KiU can move from raw book text toward provenance-rich graph assets and
candidate generation.

The main line for this version is:

`raw book -> source chunks -> extraction results -> graph -> distillation -> routing -> review`

## Book Overview v0.1

Canonical bundle locations:

- `BOOK_OVERVIEW.md`
- `ingestion/book-overview-v0.1.json`

`Book Overview` is the source-level context contract between ingestion and extraction.
It exists to give later extractors and reviewers a stable whole-book frame without
smuggling in routing decisions.

Required fields:

- `schema_version = kiu.book-overview/v0.1`
- `source_id`
- `source_file`
- `language`
- `chunk_count`
- `chapter_count`
- `section_count`
- `chapter_map`
- `thesis_summary`
- `boundary_warnings`
- `domain_tags`
- `extraction_context`

This artifact may summarize source structure, dominant theses, and boundary warnings,
but it must not assign `workflow_script` / `llm_agentic` execution modes.

## Source Chunks v0.1

Canonical schema: `schemas/source-chunks-v0.1.json`

The `source chunks` artifact is the normalized ingress contract from long-form source
material into the extraction stage.

Required top-level fields:

- `schema_version = kiu.source-chunks/v0.1`
- `bundle_id`
- `source_id`
- `source_file`
- `language`
- `chunks`

Each chunk must record:

- `chunk_id`
- `source_id`
- `source_file`
- `chapter`
- `section`
- `line_start`
- `line_end`
- `chunk_text`
- `token_estimate`
- `language`

## Extraction Results v0.1

Canonical schema: `schemas/extraction-results-v0.1.json`

`v0.6` W1 only requires an empty shell extraction result so the upstream interface can
be wired before LLM extraction lands.

Required fields:

- `schema_version = kiu.extraction-results/v0.1`
- `bundle_id`
- `source_id`
- `source_file`
- `input_chunk_count`
- `chunk_ids`
- `nodes`
- `edges`
- `warnings`

## Graph v0.2

Canonical schema: `schemas/graph-v0.2.json`

`v0.6` upgrades `graph.json` from `kiu.graph/v0.1` to `kiu.graph/v0.2` and makes
provenance first-class.

### Node fields

Each node keeps the v0.1 identity fields and adds:

- `source_file`
- `source_location`
- `extraction_kind`

### Edge fields

Each edge keeps the v0.1 topology fields and adds:

- `source_file`
- `source_location`
- `extraction_kind`
- `confidence`

### Extraction Kind

The graph must distinguish:

- `EXTRACTED`
- `INFERRED`
- `AMBIGUOUS`

This prevents the graph from collapsing into a summary blob. Every node and edge must
state whether it was directly extracted, inferred, or still ambiguous.

### Validator Expectations

`v0.6` validator behavior:

- `kiu.graph/v0.1` remains readable during the migration window
- `kiu.graph/v0.2` enforces provenance fields
- `EXTRACTED` nodes and edges require `source_file`
- `confidence` on edges must stay within `[0.0, 1.0]`
- published bundles warn when ambiguous edges exceed the configured ratio

## Migration Rule

The canonical migration entrypoint is:

```bash
python scripts/migrate_graph_v01_to_v02.py <bundle-path>
```

The migration must update:

- `graph/graph.json`
- `manifest.yaml`
- `skills/*/anchors.yaml`
- `skills/*/iterations/revisions.yaml`

## Examples Regression Set

`examples/README.md` defines the minimum v0.6 regression sample set.

The two markdown books are independent source lines for source/extraction validation,
not mixed into a single skill bundle.

## Reference Benchmark Contract

`v0.6` adds a local benchmark entrypoint so KiU artifacts can be scored against local
reference packs without turning those packs into hidden upstream inputs.

Canonical entrypoint:

```bash
python scripts/benchmark_reference_pack.py \
  --kiu-bundle bundles/poor-charlies-almanack-v0.1 \
  --reference-pack /tmp/kiu-reference-poor-charlies-almanack-skill \
  --alignment-file benchmarks/alignments/poor-charlies-vs-cangjie.yaml \
  --comparison-scope same-source
```

Optional generated-run mode:

```bash
python scripts/benchmark_reference_pack.py \
  --kiu-bundle /tmp/kiu-local-artifacts/book-pipeline/sources/<source-id>/bundle \
  --run-root /tmp/kiu-local-artifacts/book-pipeline/generated/<bundle-id>/<run-id> \
  --reference-pack /tmp/kiu-reference-poor-charlies-almanack-skill
```

The benchmark report must keep these dimensions separate:

- `output_count`
- `coverage`
- `actionability`
- `evidence_traceability`
- `workflow_vs_agentic_boundary`
- `real_usage_quality`

For quality-first same-source review, the benchmark may also emit:

- `concept_alignment`
- aligned `kiu_review`
- aligned `reference_review`
- per-pair artifact score delta

It also emits an internal scorecard for:

- `KiU foundation retained`
- `Graphify core absorbed`
- `cangjie core absorbed`

This benchmark is audit-only. Local reference packs remain `reference/benchmark`
artifacts, not default production inputs.

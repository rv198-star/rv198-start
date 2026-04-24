# KiU Skill Spec v0.6

## Positioning

`v0.6` does not replace the `v0.5` foundation. It extends the upstream half of the
pipeline so KiU can move from raw book text toward provenance-rich graph assets and
candidate generation.

The main line for this version is:

`raw book -> source chunks -> extraction results -> graph -> distillation -> routing -> review`

## Release Principles

`v0.6.0` follows five release principles.

### 1. In Use First

The first question is not whether the graph looks elegant. The first question is
whether the upstream source/evidence pipeline materially supports stronger downstream
skill/workflow production.

Therefore:

- provenance and audit quality are `P0`
- graph presentation, clustering, and report polish are strong `P1`

### 2. Graphify Core Only

`v0.6.0` absorbs only `Graphify` core:

- provenance-rich graph schema
- tri-state extraction markers
- deterministic pass plus LLM pass discipline
- graph navigation primitives

It does not treat IDE integrations, multi-language packaging, MCP serving, or export
scaffolding as release-defining work.

### 3. L4+ Handoff Maturity

The upstream production chain must be mature enough to hand off at an enterprise
information-maturity `L4+` level.

This does not mean "outsource the business." It means:

- critical intermediate assets must survive beyond a single LLM conversation
- evidence spine artifacts must be inspectable, serializable, and transferable
- model changes or operator changes must not erase provenance

### 4. Deterministic Evidence Spine, LLM Synthesis

`v0.6.0` does not require skill production without LLMs. It does require that the
evidence spine is not a black box.

Deterministic layers are responsible for:

- source chunking
- source coordinates
- schema validity
- provenance binding
- extraction audit records

LLM-required layers are responsible for:

- richer extraction
- relation disambiguation
- candidate distillation
- drafting and refinement

### 5. Boundary Discipline Preserved

Stronger upstream extraction may not be used to silently blur the
`workflow_script` / `llm_agentic` boundary. Routing quality remains a release gate,
not a secondary metric.


### 6. Bottom Layer, Not Final Usage Victory

`v0.6.0` closes the Graphify-core substrate: provenance coordinates, tri-state markers,
communities, graph reports, and evidence auditability. It does not by itself guarantee
a large final-usage lead over `cangjie-skill`, because cangjie remains strong at
trigger phrasing, action language, and short-path skill packaging.

Therefore the release gate separates two claims:

- Graphify-core absorption must close at the substrate level.
- Large final-usage overperformance belongs to the next graph-to-skill distillation
  and world-alignment lines.

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

The repository sample policy for `v0.6.0` is:

- at least `3` independent sample books live in-repo
- at least `2` act as formal production-validation samples
- `Poor Charlie's Almanack` remains a formal sample as well, but its main role is
  `benchmark-control` against the local `cangjie` reference pack

Samples must remain independent source lines. They are not mixed into a single bundle
or evaluation case.

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

For `Poor Charlie's Almanack`, the release judgment standard is `layered
overperformance`:

- `usage`
- `workflow-vs-agentic boundary quality`
- `evidence honesty`

must clearly outperform the local `cangjie` reference pack.

Count is secondary:

- KiU does not need to win by raw skill count
- but it may not fall materially behind while claiming a better topology

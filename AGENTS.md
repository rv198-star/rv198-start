# AGENTS

## External Reference Boundary

KiU may use external projects such as `cangjie-skill` and `Graphify` as local reference material, benchmark baselines, and design inspiration, but not as silent inputs to the default production pipeline.

Required rules:

- Treat external projects as `reference` or `benchmark`, not as hidden upstream generators for KiU's default artifacts.
- KiU's default generation path must consume original source materials, not external final skill packs.
- When running A/B or blind comparison, use the same source book where possible, but keep KiU outputs and external benchmark outputs produced by separate pipelines.
- Do not paste or ingest external final `SKILL.md` outputs into KiU's default candidate-building flow.
- If a teacher/reference-assisted mode is introduced later, it must be explicitly named, isolated from the default mode, and evaluated separately.
- Attribution requirements in `NOTICE` and `docs/third-party-attribution.md` remain mandatory whenever external project ideas, prompts, or structures are reused.

## Benchmark Policy

For `cangjie-skill` specifically:

- Prefer using books that `cangjie-skill` already processed as same-source benchmark corpora.
- Compare on output count, coverage, actionability, evidence traceability, workflow-vs-agentic boundary quality, and real usage quality.
- Prefer blind review when comparing KiU outputs with `cangjie-skill` outputs.

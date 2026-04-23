# Third-Party Attribution

## Purpose

This document records the external project influences explicitly referenced by the KiU
team during `v0.6` planning. The goal is to clear attribution risk early and to make
future public release hygiene straightforward.

## Current Status

- Current repository status: no third-party source files, prompts, or templates are
  vendored from the reference projects listed below.
- Current reuse model: KiU absorbs core ideas only, not the surrounding tooling surface.
- Update rule: if any future change imports upstream code, prompt text, templates, or
  documentation verbatim, update this file and the repository `NOTICE` in the same
  commit.

## Reference Projects

### Graphify

What KiU treats as the reusable core:

- provenance-rich graph schema
- source file and source location coordinates on graph artifacts
- edge-level confidence and extraction-kind metadata
- a distinction between extracted, inferred, and ambiguous relationships
- a graph report layer that helps review the graph instead of treating it as a dump

What KiU does not treat as the target for direct carry-over:

- IDE integrations
- large language/tree-sitter coverage surface
- server/runtime packaging
- export adapters and other surrounding tooling surface

How this shows up in KiU planning:

- `v0.6` uses Graphify as the benchmark for provenance-rich graph schema expectations.
- The target is a provenance-rich graph schema with auditable origin fields, not a
  one-shot summarization graph.

### cangjie-skill

What KiU treats as the reusable core:

- book-to-skill pipeline thinking
- staged extractor design
- skill-quality verification heuristics
- template-driven output discipline
- the RIA-TV++ style staged methodology for turning a long-form source into reusable
  skill artifacts

What KiU does not treat as the target for direct carry-over:

- repository-specific prompt packaging
- direct template copying without attribution review
- project-specific wording that is not needed for KiU's own schema

How this shows up in KiU planning:

- `v0.6` uses cangjie-skill as the benchmark for book-to-skill throughput and staged
  extraction methodology.
- KiU can absorb method structure such as RIA-TV++, but still needs its own schemas,
  validators, and evidence-first delivery shape.

## Practical Interpretation For KiU

- The two references are benchmark lines, not vendor dependencies.
- KiU should copy the smallest defensible core when it learns from these projects.
- KiU should not import surrounding ecosystems just because they exist upstream.
- Any future direct reuse must state exact file-level provenance and retention scope.

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

## Workflow-vs-Agentic Boundary

KiU treats the boundary between `workflow_script` and `llm_agentic` as a first-class design principle, not as an after-the-fact UI or runtime convenience.

Required rules:

- Judge the boundary on two separate axes: `workflow certainty` and `context certainty`.
- `workflow certainty` asks whether the task can be executed as a stable, repeatable, bounded procedure with low judgment variance.
- `context certainty` asks whether the required situational inputs are explicit enough that the system does not need broad interpretive reconstruction before acting.
- When both workflow certainty and context certainty are high, route the item to `workflow_script_candidate`, preserve it under `workflow_candidates/`, and keep it out of `bundle/skills/`.
- When the task still depends on judgment-rich interpretation, boundary arbitration, or context assembly, keep it on the `llm_agentic` path and treat it as a skill candidate rather than forcing it into a script.
- Never silently promote deterministic workflow logic into a KiU skill just because the prose looks rich, and never silently collapse a judgment-heavy skill into a checklist just because it can be summarized.
- Benchmark and release review must score `workflow-vs-agentic boundary quality` explicitly; content richness alone is not enough.

Current minimum implementation contract:

- Profiles own the routing rule. The default release rule today is `high workflow certainty + high context certainty => workflow_script_candidate`.
- Routed workflow candidates must remain auditable through their `candidate.yaml`, `workflow.yaml`, and supporting evidence, even though they are excluded from published `bundle/skills/`.
- Changes to extraction, seed mining, drafting, or refinement must be checked against this boundary rule so that quality gains do not come from boundary drift.

## System Efficiency Over Local Advantage

KiU treats `system-level efficiency` as a long-term strategic decision principle.
When system-level cost-efficiency gains are large enough, real local advantages may
survive only as niche exceptions rather than remain the mainline production path.

This principle exists to prevent the project from defending slow, fragile, or
unscalable local excellence out of attachment rather than clear judgment.

Required rules:

- Do not use isolated best-case outputs to deny a system direction. Long-term decisions
  must be judged on `average vs average`, not `best A vs average B`.
- Do not treat non-scalable excellence as a sufficient reason to block a more
  scalable system path.
- Favor solutions that improve `scale`, `handoff`, `auditability`, and `average
  production quality`, even when they give up some local brilliance.
- Keep the main battlefield on the system path; preserve exceptional local approaches
  only for justified niche scenarios.

Decision checks:

- Is the comparison fair, or are we using the best instance of one side against the
  average instance of the other?
- Is the claimed advantage scalable, transferable, and repeatable, or is it only a
  handcrafted exception?
- Are we defending the local advantage because it creates real system value, or
  because we are emotionally attached to it?

Boundary conditions:

- This principle is a `strategic correction lens`, not a mechanical decision rule.
- It may not be used to excuse weaker `evidence honesty`.
- It may not be used to excuse `workflow-vs-agentic boundary` drift.
- It does not override domains where irreversible harm, dignity, experience, or
  ethical floors dominate efficiency.
- It should guide long-term version strategy more than short-term transitional choices.

## Benchmark Policy

For `cangjie-skill` specifically:

- Prefer using books that `cangjie-skill` already processed as same-source benchmark corpora.
- Compare on output count, coverage, actionability, evidence traceability, workflow-vs-agentic boundary quality, and real usage quality.
- Prefer blind review when comparing KiU outputs with `cangjie-skill` outputs.

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

## Five-Step Landing Method

KiU uses the `Baseline -> Target -> Gap -> Strategy -> Breakdown` method as the
default way to handle complex planning, audit feedback, version goals, and
ambiguous engineering decisions. In Chinese shorthand: `基 -> 标 -> 差 -> 策 -> 拆`
or `基标差策拆`.

This method exists to prevent planning drift, premature implementation, and
false closure caused by unclear baselines or non-executable goals. The final
`Breakdown` step is recursive: every subproblem must be checked for executability.
If a subproblem still cannot be started, tested, or judged tomorrow, run the full
`Baseline -> Target -> Gap -> Strategy -> Breakdown` loop again on that subproblem
until it becomes an action.

Required sequence:

- `Baseline`: define the current state with facts, evidence, and known limits.
  Ask: where are we now, and what is already proven?
- `Target`: define the desired end state and acceptance criteria. Ask: where are
  we going, and what measurable condition means we have arrived?
- `Gap`: identify the concrete distance between baseline and target. Ask: what
  is missing across capability, evidence, resources, path, or understanding?
- `Strategy`: choose the route for crossing the gap. Ask: which path gives the
  best tradeoff under current constraints, and what are we deliberately not
  doing?
- `Breakdown`: decompose the strategy into executable actions. Ask: what can be
  started next, by whom or by which agent, with what input, output, and judging
  criteria? For each subproblem, ask `is this executable now?`; if not, recursively
  apply the same five-step method to that subproblem.

Required outputs for non-trivial work:

- A baseline summary or fact list before target claims.
- Target criteria that can be verified, not just described.
- A gap list that names missing evidence or missing capability explicitly.
- A strategy choice with rejected alternatives or tradeoffs when more than one
  path is plausible.
- An action list where each item has enough detail to execute, test, and review.
- For any non-executable subproblem, a nested five-step pass instead of a vague task.

Decision checks:

- Are we solving from the real baseline, or from an assumed state?
- Is the target measurable enough to reject false completion?
- Did we name the actual gaps, or only restate the desired outcome?
- Is the strategy an explicit choice, or just a list of hopeful activities?
- Can every action be started and judged without further vague interpretation?
- For every item that is not executable yet, did we recurse instead of pretending
  it is an action?

Boundary conditions:

- This method does not override evidence honesty, workflow-vs-agentic boundary
  rules, or external reference boundaries.
- It should be used more rigorously as complexity, uncertainty, or audit risk
  increases.
- For small tasks, it can be compressed into a brief mental or written checklist,
  but the order must remain: baseline before target, target before gap, gap before
  strategy, strategy before breakdown.
- The method terminates only when the leaf nodes are executable actions with input,
  output, owner or agent, verification command, and acceptance criteria.

## Benchmark Policy

For `cangjie-skill` specifically:

- Prefer using books that `cangjie-skill` already processed as same-source benchmark corpora.
- Compare on output count, coverage, actionability, evidence traceability, workflow-vs-agentic boundary quality, and real usage quality.
- Prefer blind review when comparing KiU outputs with `cangjie-skill` outputs.

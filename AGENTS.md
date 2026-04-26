# AGENTS


## Project Identity

Starting with `v0.7`, KiU's Chinese project name is `学以致用`.

This name is not a cosmetic translation. It reinforces the project goal: source
knowledge should become executable action capacity while preserving evidence,
boundaries, and user choice about whether to apply additional context layers.

Required rules:

- Keep `KiU` as the stable technical/project abbreviation.
- Use `学以致用` as the Chinese-facing project name from `v0.7` onward.
- Do not rename historical release evidence retroactively; older artifacts may remain
  under `Knowledge in Use` / `KiU` wording for provenance clarity.

## v0.8 Language Migration Boundary

Starting with v0.8, new mainline project documents should explain KiU through
the `学以致用` architecture language before using historical release or
reference-project terminology.

Required rules:

- Do not rewrite historical reports, release evidence, old plans, or attribution
  records just to rename terms.
- Keep historical terms available in `docs/concept-language-glossary.md` for
  traceability.
- New public-facing docs should lead with: 读准原书, 提炼判断, 生成技能,
  分流流程, 校准应用, and 验证行动价值.
- Historical terms such as Graphify absorption, cangjie methodology absorption,
  RIA-TV++, C-class, and world alignment may appear in new docs only when
  explicitly labeled as historical/internal terminology or when required for
  attribution.
- Use `技能不是摘要` and `学到最后要能用` as the two preferred public phrases.
  Keep `用而不染` as the application-calibration boundary principle.
  Do not introduce additional branded terminology unless it removes more
  confusion than it adds.
- README and release notes should lead with the new architecture language, not
  release-history vocabulary.

## World Alignment Isolation Boundary

KiU `v0.7` world alignment follows `isolation enhancement`, not `fusion rewrite`.
World alignment may add a separate contextual review, gate, pressure-test, or
usage-caveat layer, but it must not rewrite source-faithful skills into
world-blended artifacts.

This principle preserves compatibility with users who want an original-source-only
mode. A user must be able to request source-faithful KiU outputs without world
alignment being applied.

Required rules:

- Keep source-derived `SKILL.md`, anchors, rationale, and book claims source-faithful.
- Store world context, temporal caveats, pressure tests, and application gates in
  isolated artifacts such as `world_alignment/`, not as silent edits to the skill.
- World alignment may change application advice (`apply`, `partial_apply`,
  `apply_with_caveats`, `ask_more_context`, `refuse`), but not the source claim.
- Preserve an explicit original-source-only path for users who do not want real-world
  alignment applied.
- Do not use external world context as hidden source evidence or as a replacement
  for book/source anchors.
- Release evidence must score `source_fidelity_preserved` and
  `world_context_isolated` separately from practical usefulness.

Decision checks:

- Can a reviewer see which parts came from the source and which parts came from
  world alignment?
- Can the same skill be used in original-source-only mode without the world layer?
- Did world context merely gate or caveat application, or did it silently rewrite
  the author's/source's claim?
- Are we improving practical usefulness without weakening evidence honesty or the
  workflow-vs-agentic boundary?

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

## Recursive Five-Step Method

KiU uses the recursive `Baseline -> Target -> Gap -> Strategy -> Breakdown`
method as the default way to handle complex planning, audit feedback, version
goals, ambiguous engineering decisions, and action-value evaluation. In Chinese
shorthand: `基 -> 标 -> 差 -> 策 -> 拆` or `基标差策拆`.

This method is no longer limited to solving an already-known problem. KiU applies
the same five-step loop across three layers: discovering signals from the world,
defining those signals into falsifiable problems, and resolving those problems
into executable actions. The method exists to prevent planning drift, premature
implementation, shallow problem statements, and false closure caused by unclear
baselines or non-executable goals.

Layer model:

- `L1 Discover`: world -> signal. Use `Baseline -> Target -> Gap -> Strategy ->
  Breakdown` to turn a noisy situation into a signal that can be restated,
  located, and reproduced. The breakdown output is an observation action, not a
  solution.
- `L2 Define`: signal -> problem. Use `Baseline -> Target -> Gap -> Strategy ->
  Breakdown` to turn a signal into a problem statement that is falsifiable and
  measurable. The breakdown output is a precise problem statement, not an action
  plan.
- `L3 Resolve`: problem -> action. Use `Baseline -> Target -> Gap -> Strategy ->
  Breakdown` to turn a defined problem into actions with inputs, outputs,
  owners or agents, verification commands, and acceptance criteria.
- `Feedback`: execution -> recalibration. Use decision logs, pre-mortems, hit-rate
  ledgers, or hypothesis ledgers to feed execution results back into `L1`, `L2`,
  or `L3` instead of treating one answer as final.

Required sequence inside every layer:

- `Baseline`: define the current state with facts, evidence, and known limits.
  Ask: where are we now, what is already proven, and what is only assumed?
- `Target`: define the desired end state and acceptance criteria. Ask: where are
  we going, and what observable condition means this layer has succeeded?
- `Gap`: identify the concrete distance between baseline and target. Ask: what
  is missing across evidence, capability, resources, path, or understanding?
- `Strategy`: choose the route for crossing the gap. Ask: which path gives the
  best tradeoff under current constraints, and what are we deliberately not
  doing?
- `Breakdown`: decompose the strategy into the correct output for the current
  layer. For `L1`, produce observation actions. For `L2`, produce a falsifiable
  problem statement. For `L3`, produce executable actions. For every subproblem,
  ask `is this executable, testable, or judgeable now?`; if not, recursively apply
  the same five-step loop to that subproblem.

Required outputs for non-trivial work:

- A baseline summary or fact list before target claims.
- Target criteria that can be verified, not just described.
- A gap list that names missing evidence or missing capability explicitly.
- A strategy choice with rejected alternatives or tradeoffs when more than one
  path is plausible.
- A layer-appropriate breakdown: observation actions for discovery, falsifiable
  problem statements for definition, executable actions for resolution.
- A feedback or falsification hook when decisions depend on uncertain assumptions.
- For any non-executable subproblem, a nested five-step pass instead of a vague
  task.

Decision checks:

- Are we discovering the real signal, or solving the most visible symptom?
- Are we defining a falsifiable problem, or restating a preference, complaint, or
  conclusion?
- Are we solving from the real baseline, or from an assumed state?
- Is the target measurable enough to reject false completion?
- Did we name the actual gaps, or only restate the desired outcome?
- Is the strategy an explicit choice, or just a list of hopeful activities?
- Can every action be started and judged without further vague interpretation?
- For every item that is not executable, testable, or judgeable yet, did we
  recurse instead of pretending it is an action?
- Is there a feedback ledger or falsification mechanism for uncertain decisions?

Boundary conditions:

- This method does not override evidence honesty, workflow-vs-agentic boundary
  rules, world-alignment isolation, or external reference boundaries.
- It should be used more rigorously as complexity, uncertainty, or audit risk
  increases.
- For small tasks, it can be compressed into a brief mental or written checklist,
  but the order must remain: baseline before target, target before gap, gap before
  strategy, strategy before breakdown.
- The method terminates only when leaf nodes are observation actions, falsifiable
  problem statements, or executable actions with enough input, output, verification,
  and acceptance criteria to be judged.
- A high-quality KiU skill may create action value at any layer. It does not need
  to force every user request into direct execution if the real value is signal
  discovery, problem definition, or feedback calibration.



## Verification Feedback Discipline

Long verification runs must be split into visible stages with progress feedback.
Do not stay silent until a full suite finishes when the run is likely to take more
than a few seconds. The user should be able to see which verification phase is
running, what has already passed, and what remains.

Required rules:

- Prefer staged verification: targeted tests first, affected subsystem tests next,
  full-suite discovery last.
- Report after each stage with the command scope and result count.
- When a full suite is necessary, announce it before starting and provide interim
  updates while it is running.
- If a command is still running, poll and summarize progress instead of waiting
  silently for the final output.
- Do not present a release or completion claim until the required stages have fresh
  passing evidence.
- If time is limited, say which verification tier has passed and which tier remains
  unrun instead of implying full coverage.

Recommended sequence for feature work:

1. New or changed behavior tests.
2. Affected module or subsystem test file.
3. Version-specific regression subset.
4. YAML/schema/documentation sanity checks.
5. Full repository test discovery only after the earlier stages pass.

## Version Goal Tiers

KiU separates short-term development goals from condition-dependent external
validation. This keeps development executable when reviewers, real users, live web
access, or domain experts are not currently available.

Required rules:

- Treat `developable goals` as the short-term release driver: architecture, source
  fidelity, installability, workflow-vs-agentic boundary quality, internal usage
  regression, proxy pressure tests, cross-sample stability, and evidence honesty.
- Treat `condition-dependent goals` as mid/late-stage validation: human blind
  review, real user preference, live-world factual verification, domain-expert
  review, and long-running production usage data. These goals are valuable, but
  they must not block short-term releases when the required external condition is
  unavailable.
- Treat `strategic vision` as a north star rather than a release gate: proving KiU
  is preferred in real-world use, building high-quality world modeling, and
  outperforming reference projects under external review.
- Do not upgrade claims from internal evidence to external validation. If a release
  only has internal regression, proxy usage, or same-book reference comparison, say
  so explicitly.
- Do not open a short-term version whose central acceptance criterion depends on
  unavailable external conditions. Move that work to future backlog until the
  condition exists.

Decision checks:

- Can this goal be executed and verified with resources available now?
- If not, is it clearly marked as condition-dependent rather than a blocker?
- Does the release claim match the strongest available evidence tier?
- Are we continuing to improve the system rather than waiting for ideal validation?

Boundary conditions:

- External validation remains important for mature claims, but it is not the daily
  development engine.
- Internal evidence may justify continued development and foundation releases; it
  may not justify claims of human preference, real-world truth, or external closure.

## Benchmark Policy

For `cangjie-skill` specifically:

- Prefer using books that `cangjie-skill` already processed as same-source benchmark corpora.
- Compare on output count, coverage, actionability, evidence traceability, workflow-vs-agentic boundary quality, and real usage quality.
- Prefer blind review when comparing KiU outputs with `cangjie-skill` outputs, but treat it as condition-dependent evidence rather than a short-term blocker when no reviewer is available.

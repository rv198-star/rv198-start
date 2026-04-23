# KiU Version Roadmap Realignment (`v0.5.1` / `v0.6` / `v0.7`)

Date: `2026-04-24`

## Purpose

This document freezes the current version split so the repo stops mixing three different
goals into one line:

- `v0.5.1` = the corrective line that closed the `cangjie-skill`
  same-source / same-scenario gap under the stricter current target
- `v0.6` = the reserved next line for absorbing the `Graphify` core on the
  source / graph / provenance side
- `v0.7` = the later reserved major line for `In Use world-alignment`

The split exists for one reason: these are related, but not equivalent, problems.
If they stay mixed together, any gain or regression becomes hard to attribute.

## Stable Version Wording

Use the wording below in repo docs and release notes:

- `v0.5.0` completed KiU's foundation line.
- `v0.5.1` completed the corrective line for the local `cangjie-skill`
  benchmark gap under the stricter "small but real overperformance" requirement.
- `v0.6` is the future `Graphify` alignment line: provenance-rich graph,
  tri-state extraction, upstream extraction discipline, and graph navigation.
- `v0.7` is the later `In Use world-alignment` line: real-world usefulness,
  realism pressure, and abstraction-preserving practical alignment.

## Why `In Use world-alignment` Is Not Part Of `v0.6`

`Graphify` and `In Use world-alignment` improve different layers:

- `Graphify` asks: can KiU represent where knowledge came from, how strong it is,
  and how the graph can be navigated and audited?
- `In Use world-alignment` asks: does the generated skill help in a real decision
  context without collapsing into overfit scripts, shallow advice, or boundary drift?

Those layers interact, but they should not share a single release claim:

- if both are done in one version, improvements become hard to attribute
- if one succeeds and the other regresses, the version story becomes muddy
- `In Use world-alignment` needs its own gate because it must balance realism with
  abstraction and generalization rather than just increasing direct-use flavor

Therefore:

- `v0.6` stays source-side and graph-side
- `v0.7` gets the separate world-alignment mandate

## What `cangjie-skill` Still Does Better

The local `poor-charlies-almanack-skill` reference pack remains a useful benchmark
because it is very strong in direct usability:

- trigger phrasing is close to how real users talk
- the packs read like ready-to-use skill cards rather than audit-first specs
- neighboring skills are often split in a way that makes invocation obvious
- the README and examples sell actionability immediately

That is the part KiU still needs to keep tightening in `v0.5.1`.

## What `cangjie-skill` Still Does Worse

The same local reference pack also shows clear limits that matter to KiU's direction:

- evidence traceability is weak compared with KiU's double-anchor model; it is hard to
  audit why a specific claim or boundary exists
- `workflow` vs `agentic` routing is implicit rather than first-class, so everything is
  pulled toward skill form even when some outputs would be better delivered as scripts
- release and revision discipline are thin; there is no KiU-style production gate,
  three-layer review, or explicit "manual revision vs loop-driven revision" accounting
- long-term graph evolution is limited; the pack is easier to consume than to merge,
  compare, or evolve across bundles
- count advantage can hide overlap; more skills does not by itself prove cleaner
  boundaries, deeper abstraction, or better topology

These are the reasons KiU should not optimize toward "be more like cangjie everywhere".

## How KiU Can Keep Winning Without Graphify-Style Source Expansion

Even without strengthening the source layer, KiU can still outperform `cangjie` on the
production side by pushing five levers:

1. `usage-first drafting`
   - make generated `Contract`, `Rationale`, and `Usage Summary` read like deployment
     artifacts rather than review leftovers
2. `better family topology`
   - prefer parent skill + specialist skill structures over accidental partial-overlap
     comparisons
3. `failure-taxonomy repair`
   - keep closing `boundary_leak`, `generic_reasoning`, `next_step_blunt`, and
     `edge_case_collapse` through benchmark-driven repair rather than ad hoc rewrites
4. `boundary-preserved directness`
   - improve realism and next-step usefulness without converting workflow-like material
     into fake agentic skills
5. `honest release gates`
   - treat benchmark win, artifact quality, and boundary discipline as simultaneous
     conditions rather than claiming success from any one layer alone

This is the correct interpretation of the released `v0.5.1` evidence:

- KiU's strongest positive evidence did not come from stronger source provenance
- the encouraging gains came from making the same-source output more usable while
  preserving stricter boundary and audit discipline
- that evidence is sufficient for the `v0.5.1` release claim, but it does not
  change the separate goals reserved for `v0.6` and `v0.7`

## `v0.6` Scope Freeze

`v0.6` should now be judged on the following source-side and graph-side questions:

- Is raw-book ingestion more explicit and auditable?
- Does extraction output carry provenance and tri-state confidence?
- Does graph navigation improve through clustering, report generation, and cross-bundle
  synthesis?
- Does the stronger upstream layer improve downstream candidate quality without breaking
  the workflow-vs-agentic boundary?
- Does the repo gain a project-state layer such as a native `backlog/kanban` asset so
  multi-session AI execution does not depend only on local plan documents and therefore
  lose version-level continuity?

`v0.6` should not be judged on:

- whether KiU already solved real-world alignment
- whether generated language sounds maximally practical in every scenario
- whether the system simulates real-world pressure or adversarial stakeholder games

Those belong to `v0.7`.

## `v0.7` Mandate

`v0.7` should be treated as a separate major version because it introduces a new primary
question:

> Can KiU generate skills that remain abstract and transferable while also surviving
> realistic use pressure?

That version must balance:

- `realism` vs `abstraction`
- `actionability` vs `overfitting`
- `world grounding` vs `source fidelity`
- `practical usefulness` vs `workflow-boundary discipline`

The world-alignment layer must stay a reviewer / simulator / critic, not a hidden source
of facts.

It may:

- stress-test trigger realism
- pressure-test next-step usefulness
- detect boundary drift under realistic incentives
- simulate user misunderstanding, incomplete context, or stakeholder pressure

It may not:

- invent source claims
- overwrite authorial evidence
- silently expand a skill beyond its valid boundary

## Execution Order

Recommended order going forward:

1. finish `v0.5.1` and only sign it off after stable "small but real" benchmark
   overperformance is accepted
2. then continue `v0.6` as the `Graphify` absorption line only
3. then define `v0.7` as a separate major research and implementation track

`2026-04-24` update:

- step `1` is now complete
- the corrective line is frozen as released
- backlog and implementation attention can move to `v0.6`

This keeps KiU's version history honest:

- `v0.5.1` = released corrective benchmark line
- `v0.6` = later source / graph strengthening line
- `v0.7` = later practical world-alignment line

## `v0.6.0` Additional Backlog Item

To avoid project-state drift in long AI-led work, `v0.6.0` should also add a
repo-native project-management surface alongside specs and plans:

- a canonical `backlog` / `kanban` asset with ticket status, priority, target version,
  blocker level, acceptance criteria, and evidence links
- explicit links from each backlog item to spec, plan, benchmark, and release artifacts
- session-close updates so partially completed work and non-blocking leftovers stop
  disappearing into chat history

The canonical path for this surface is now:

- `backlog/board.yaml`
- `python3 scripts/show_backlog.py --version v0.6.0`

This is not a `v0.5.1` release gate item. It is intentionally deferred into the
`v0.6.0` line as project-scale execution infrastructure.

# `cangjie-skill` Shortfalls And KiU Overperformance Strategy

Date: `2026-04-24`

## Scope

This note records the current project judgment after reviewing the local
`poor-charlies-almanack-skill` reference pack and the latest KiU same-source benchmark
archives.

The question is not "how to imitate `cangjie-skill` more closely".

The real question is:

> What did `cangjie-skill` do right, what are its real limits, and how should KiU exceed
> it without relying on stronger source-layer support?

## What `cangjie-skill` Gets Right

`cangjie-skill` remains strong in four areas:

- direct-use framing: the packs read like tools rather than review artifacts
- trigger realism: the activation language sounds close to real user speech
- fast actionability: outputs move quickly toward "what to do next"
- throughput / granularity pressure: the pack exposes more candidate slots and therefore
  forces KiU to justify why fewer skills are actually better

This is why `cangjie-skill` is a valid benchmark pressure source even though KiU has the
stronger structural schema.

## What `cangjie-skill` Leaves Weak

For KiU's goals, the local reference pack still has structural weaknesses:

### 1. Provenance And Auditability

The pack is good to read but hard to audit.

- evidence is embedded in prose rather than formal anchor systems
- it is hard to trace one judgment back to a graph object or canonical evidence pool
- long-term maintenance depends heavily on implicit human interpretation

### 2. Workflow vs Agentic Boundary

The pack defaults toward "skillifying" everything.

- deterministic procedural material is not cleanly separated into workflow artifacts
- boundary quality is not treated as an explicit release dimension
- this makes the pack feel immediately useful, but it weakens route discipline

### 3. Revision And Release Engineering

The pack has methodology, but weak release accounting.

- there is no KiU-style production gate
- no three-layer review contract
- no explicit distinction between manual revision and loop-driven improvement
- benchmark and release claims are harder to audit as the pack evolves

### 4. Topology And Overlap Risk

Higher skill count creates pressure, but also overlap risk.

- count alone does not prove a cleaner concept topology
- neighboring skills can become loosely separated usage slices rather than stable,
  generalizable abstractions
- this makes the pack strong for immediate invocation and weaker for long-term knowledge
  architecture

## What KiU Must Not Do

KiU should not respond to the benchmark by making three mistakes:

- do not treat higher skill count as automatic proof of better output
- do not relax `workflow-vs-agentic` routing just to look more directly usable
- do not use benchmark wins as permission to abandon audit structure

Those moves would copy the reference pack's strengths by also copying its limits.

## What KiU Has Demonstrated So Far In `v0.5.1`

The strongest `v0.5.1` evidence so far is positive, but still narrow and specific:

- KiU has shown same-scenario usage improvement strong enough to produce encouraging
  benchmark wins on some archived evidence
- KiU has kept `workflow-vs-agentic` boundary discipline intact in that evidence
- KiU did not need stronger source provenance to produce those gains

The important lesson is that KiU's best path is not "more reference imitation".

It is:

- keep the stronger structural discipline
- make the generated artifacts read and behave more like deployable tools

## Non-Graphify Strategy To Stay Ahead

Without changing the source layer, KiU should keep improving five things:

### 1. Usage-Language Compression

Generated artifacts must stop sounding like internal review leftovers.

- `Contract` should expose live trigger language
- `Rationale` should justify the judgment without sounding academic
- `Usage Summary` should tell the operator what to do next with low friction

### 2. Parent / Specialist Skill Topology

KiU should prefer explicit concept families over accidental overlap.

Example:

- parent valuation skill for "is this worth doing / buying at all?"
- specialist sizing skill for "if yes, how hard can I lean?"

This improves alignment, benchmark fairness, and operator clarity.

### 3. Failure-Tag-Driven Repair

The repair loop should stay tied to actual usage failure categories:

- `boundary_leak`
- `generic_reasoning`
- `next_step_blunt`
- `edge_case_collapse`

This is better than broad "rewrite to sound better" editing because it preserves an
auditable reason for each quality lift.

### 4. Boundary-Preserved Practicality

KiU should increase realism and directness without changing route ownership.

- workflow material should still become `workflow_candidates`
- judgment-heavy material should still become skills
- benchmark wins must come from better handling of the same job, not from moving the job

### 5. Honest Version Narrative

KiU should keep separating these claims:

- foundation complete
- same-source benchmark gap closed
- source/provenance line upgraded
- world-alignment achieved

This protects the project from declaring a broad win on narrow evidence.

## Strategic Consequence

The review supports the current split:

- `v0.5.1` remains the active `cangjie-skill` gap-closure line
- `v0.6` is the later `Graphify` core absorption line
- `v0.7` is the later `In Use world-alignment` line

That split is not cosmetic. It reflects three different ways KiU can improve:

- better usage behavior on the same source
- better source / graph / provenance infrastructure
- better realism under real-world pressure without losing abstraction

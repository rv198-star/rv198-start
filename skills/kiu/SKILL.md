---
name: kiu
description: Use when working with KiU, Knowledge in Use / 学以致用, to generate, review, export, or install bounded action skills from source books.
---

# KiU

KiU means `Knowledge in Use`, Chinese name `学以致用`.

Use this skill when the user wants to work with the KiU project itself: understand its boundaries, inspect review packs, generate skills from source material, export generated skills, or install KiU-generated skills.

## Operating Rules

- Treat KiU as a source-to-action-skill pipeline, not as a summarizer.
- Preserve evidence boundaries: internal scores are not external blind review, real-user validation, or domain-expert validation.
- Do not treat `review-pack/current` as the install package; it is the audit view.
- Use `installable-skills/` for generated skills that should be installed.

## References

- For evidence and boundary rules, read `references/project-boundaries.md`.
- For generation and review workflow, read `references/generation-workflow.md`.
- For export and installation workflow, read `references/distribution-workflow.md`.

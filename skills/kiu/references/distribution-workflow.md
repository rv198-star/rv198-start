# Distribution Workflow

Use `installable-skills/` when the user wants installable generated skills.

Default workflow:

1. Export from `review-pack/current` using `scripts/export_installable_skills.py`.
2. Confirm each installable skill directory has a globally unique name.
3. Confirm each directory contains `SKILL.md` with valid frontmatter.
4. Install individual skills from GitHub path, or copy them into a local `$CODEX_HOME/skills` directory for local smoke testing.
5. Restart Codex after installing skills.

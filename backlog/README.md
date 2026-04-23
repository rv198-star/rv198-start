# KiU Backlog

`backlog/board.yaml` is the repo-native project-state surface for KiU.

It exists to keep cross-session execution anchored in the repository rather than only
in chat history or scattered plan files.

Current contract:

- `board.yaml` is the canonical source of ticket state.
- Each ticket records `target_version`, `status`, `priority`, `blocker_level`,
  acceptance criteria, and evidence links.
- Tickets may point to specs, plans, reports, or release evidence, but those files are
  supporting artifacts rather than the canonical status surface.
- `scripts/show_backlog.py` is the stable read entrypoint for humans and agents.

Status enum:

- `todo`
- `in_progress`
- `blocked`
- `review`
- `done`

This asset is intentionally lightweight in `v0.5.1`: it solves project-state
continuity without introducing a new external service dependency.

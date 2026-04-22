from __future__ import annotations

import os
from pathlib import Path


DEFAULT_LOCAL_OUTPUT_ROOT = Path("/tmp/kiu-local-artifacts")


def resolve_output_root(
    raw_output_root: str | None,
    *,
    bucket: str,
) -> Path:
    """Resolve an explicit output root or the fixed local artifact root."""
    if raw_output_root:
        return Path(raw_output_root).expanduser()

    base_root = Path(
        os.environ.get("KIU_LOCAL_OUTPUT_ROOT", DEFAULT_LOCAL_OUTPUT_ROOT.as_posix())
    )
    return base_root.expanduser() / bucket

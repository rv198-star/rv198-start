#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.profile_resolver import resolve_profile


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: show_profile.py <bundle-path>")
        return 2

    profile = resolve_profile(sys.argv[1])
    print(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

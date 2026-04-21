#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_validator.core import validate_bundle


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_bundle.py <bundle-path>")
        return 2

    report = validate_bundle(sys.argv[1])
    if report["errors"]:
        print("INVALID")
        print(json.dumps(report["errors"], ensure_ascii=False, indent=2))
        return 1

    print(
        "VALID "
        + json.dumps(
            {
                "bundle_version": report["manifest"]["bundle_version"],
                "skills": len(report["skills"]),
                "graph": report["graph"],
                "shared_assets": report["shared_assets"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

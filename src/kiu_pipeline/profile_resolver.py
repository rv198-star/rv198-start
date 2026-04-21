from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any
import warnings

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PROFILES_ROOT = REPO_ROOT / "shared_profiles"
LEGACY_REFINER_KEY = "autonomous_refiner"
REFINEMENT_SCHEDULER_KEY = "refinement_scheduler"


def resolve_profile(bundle_path: str | Path) -> dict[str, Any]:
    return deepcopy(_resolve_profile_cached(str(Path(bundle_path).resolve())))


@lru_cache(maxsize=32)
def _resolve_profile_cached(bundle_root_raw: str) -> dict[str, Any]:
    bundle_root = Path(bundle_root_raw)
    manifest = _load_yaml(bundle_root / "manifest.yaml")
    domain = manifest.get("domain")
    if not domain:
        raise ValueError(f"{bundle_root}: manifest missing required domain")

    bundle_profile = _load_yaml(bundle_root / "automation.yaml")
    inherits = bundle_profile.get("inherits", domain)
    default_profile = _load_yaml(SHARED_PROFILES_ROOT / "default" / "profile.yaml")
    domain_profile_path = SHARED_PROFILES_ROOT / inherits / "profile.yaml"
    if not domain_profile_path.exists():
        raise FileNotFoundError(f"missing domain profile for {inherits}: {domain_profile_path}")
    domain_profile = _load_yaml(domain_profile_path)

    bundle_overrides = dict(bundle_profile)
    bundle_overrides.pop("inherits", None)
    bundle_overrides = _normalize_profile_aliases(bundle_overrides)

    resolved = _deep_merge(default_profile, domain_profile)
    resolved = _deep_merge(resolved, bundle_overrides)
    resolved = _normalize_profile_aliases(resolved)
    resolved["domain"] = domain
    resolved["resolved_from"] = ["default", inherits, "bundle"]
    return resolved


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_profile_aliases(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(profile)
    if LEGACY_REFINER_KEY in normalized:
        warnings.warn(
            f"{LEGACY_REFINER_KEY} is deprecated; use {REFINEMENT_SCHEDULER_KEY}",
            DeprecationWarning,
            stacklevel=2,
        )
        normalized.setdefault(REFINEMENT_SCHEDULER_KEY, normalized[LEGACY_REFINER_KEY])
        normalized.pop(LEGACY_REFINER_KEY, None)
    return normalized

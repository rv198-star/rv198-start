from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .local_paths import resolve_output_root


INVESTING_BUNDLE_ID = "poor-charlies-almanack-v0.1"
ENGINEERING_BUNDLE_ID = "engineering-postmortem-v0.1"

DEFAULT_V06_CHECK_IDS = (
    "unit-tests",
    "validate-investing-merge",
    "validate-engineering-merge",
    "build-investing",
    "review-investing",
    "build-engineering",
    "review-engineering",
)


@dataclass(frozen=True)
class RegressionCheck:
    check_id: str
    description: str
    command: tuple[str, ...]


def resolve_regression_output_root(raw_output_root: str | None) -> Path:
    return resolve_output_root(raw_output_root, bucket="regression-baseline")


def build_v06_regression_checks(
    *,
    repo_root: str | Path,
    output_root: str | Path,
    python_executable: str,
) -> list[RegressionCheck]:
    repo_root = Path(repo_root)
    output_root = Path(output_root)
    scripts_root = repo_root / "scripts"
    bundles_root = repo_root / "bundles"

    investing_bundle = bundles_root / INVESTING_BUNDLE_ID
    engineering_bundle = bundles_root / ENGINEERING_BUNDLE_ID
    generated_root = output_root / "generated"

    investing_run_root = generated_root / INVESTING_BUNDLE_ID / "baseline-investing"
    engineering_run_root = generated_root / ENGINEERING_BUNDLE_ID / "baseline-engineering"

    return [
        RegressionCheck(
            check_id="unit-tests",
            description="Run the repository unittest suite.",
            command=(
                python_executable,
                "-m",
                "unittest",
                "discover",
                "tests",
            ),
        ),
        RegressionCheck(
            check_id="validate-investing-merge",
            description="Validate the investing bundle merged against engineering.",
            command=(
                python_executable,
                str(scripts_root / "validate_bundle.py"),
                str(investing_bundle),
                "--merge-with",
                str(engineering_bundle),
            ),
        ),
        RegressionCheck(
            check_id="validate-engineering-merge",
            description="Validate the engineering bundle merged against investing.",
            command=(
                python_executable,
                str(scripts_root / "validate_bundle.py"),
                str(engineering_bundle),
                "--merge-with",
                str(investing_bundle),
            ),
        ),
        RegressionCheck(
            check_id="build-investing",
            description="Run the refinement build for the investing bundle.",
            command=(
                python_executable,
                str(scripts_root / "build_candidates.py"),
                "--source-bundle",
                str(investing_bundle),
                "--output-root",
                str(generated_root),
                "--run-id",
                "baseline-investing",
                "--drafting-mode",
                "deterministic",
            ),
        ),
        RegressionCheck(
            check_id="review-investing",
            description="Score the investing generated run with three-layer review.",
            command=(
                python_executable,
                str(scripts_root / "review_generated_run.py"),
                "--run-root",
                str(investing_run_root),
                "--source-bundle",
                str(investing_bundle),
                "--usage-review-dir",
                str(investing_run_root / "usage-review"),
            ),
        ),
        RegressionCheck(
            check_id="build-engineering",
            description="Run the refinement build for the engineering bundle.",
            command=(
                python_executable,
                str(scripts_root / "build_candidates.py"),
                "--source-bundle",
                str(engineering_bundle),
                "--output-root",
                str(generated_root),
                "--run-id",
                "baseline-engineering",
                "--drafting-mode",
                "deterministic",
            ),
        ),
        RegressionCheck(
            check_id="review-engineering",
            description="Score the engineering generated run with three-layer review.",
            command=(
                python_executable,
                str(scripts_root / "review_generated_run.py"),
                "--run-root",
                str(engineering_run_root),
                "--source-bundle",
                str(engineering_bundle),
                "--usage-review-dir",
                str(engineering_run_root / "usage-review"),
            ),
        ),
    ]


def run_v06_regression_baseline(
    *,
    repo_root: str | Path,
    output_root: str | Path | None = None,
    python_executable: str,
    only: Iterable[str] | None = None,
    skip: Iterable[str] | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    resolved_output_root = resolve_regression_output_root(
        str(output_root) if output_root is not None else None
    )
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    logs_root = resolved_output_root / "logs"
    reports_root = resolved_output_root / "reports"
    logs_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)

    checks = build_v06_regression_checks(
        repo_root=repo_root,
        output_root=resolved_output_root,
        python_executable=python_executable,
    )
    selected_checks = _select_checks(checks, only=only, skip=skip)
    env = _build_subprocess_env(repo_root)
    runs = _build_run_index(repo_root=repo_root, output_root=resolved_output_root)
    results: list[dict[str, Any]] = []

    for check in selected_checks:
        if check.check_id.startswith("review-"):
            domain = check.check_id.removeprefix("review-")
            write_usage_review_fixtures(**runs[domain])

        start = time.perf_counter()
        completed = subprocess.run(
            check.command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        stdout_log = logs_root / f"{check.check_id}.stdout.log"
        stderr_log = logs_root / f"{check.check_id}.stderr.log"
        stdout_log.write_text(completed.stdout, encoding="utf-8")
        stderr_log.write_text(completed.stderr, encoding="utf-8")

        result = {
            "check_id": check.check_id,
            "description": check.description,
            "command": list(check.command),
            "returncode": completed.returncode,
            "ok": completed.returncode == 0,
            "duration_ms": duration_ms,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "stdout_excerpt": _tail(completed.stdout),
            "stderr_excerpt": _tail(completed.stderr),
        }
        results.append(result)

        if check.check_id.startswith("build-") and completed.returncode == 0:
            domain = check.check_id.removeprefix("build-")
            payload = _parse_json_stdout(completed.stdout)
            if payload:
                runs[domain]["build_payload"] = payload

        if check.check_id.startswith("review-") and completed.returncode == 0:
            domain = check.check_id.removeprefix("review-")
            payload = _parse_json_stdout(completed.stdout)
            if payload:
                runs[domain]["review_payload"] = payload
            runs[domain]["three_layer_review_exists"] = (
                runs[domain]["run_root"] / "reports" / "three-layer-review.json"
            ).exists()

        if completed.returncode != 0:
            break

    failed = sum(1 for item in results if not item["ok"])
    passed = sum(1 for item in results if item["ok"])
    report_path = reports_root / "v0.6-regression-baseline.json"
    report = {
        "version": "kiu.regression-baseline/v0.6",
        "repo_root": str(repo_root),
        "python_executable": python_executable,
        "output_root": str(resolved_output_root),
        "planned_check_ids": [check.check_id for check in checks],
        "selected_check_ids": [check.check_id for check in selected_checks],
        "results": results,
        "runs": {
            domain: {
                "bundle_id": run["bundle_id"],
                "bundle_path": str(run["bundle_path"]),
                "run_id": run["run_id"],
                "run_root": str(run["run_root"]),
                "usage_review_dir": str(run["usage_review_dir"]),
                "three_layer_review_exists": bool(run["three_layer_review_exists"]),
            }
            for domain, run in runs.items()
        },
        "summary": {
            "executed": len(results),
            "passed": passed,
            "failed": failed,
            "aborted_after_failure": failed > 0 and len(results) < len(selected_checks),
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def write_usage_review_fixtures(
    *,
    bundle_id: str,
    run_root: Path,
    bundle_path: Path,
    run_id: str,
    usage_review_dir: Path,
    three_layer_review_exists: bool,
    build_payload: dict[str, Any] | None = None,
    review_payload: dict[str, Any] | None = None,
) -> None:
    del bundle_path, run_id, three_layer_review_exists, build_payload, review_payload
    usage_review_dir.mkdir(parents=True, exist_ok=True)
    docs = _usage_review_docs(bundle_id=bundle_id, run_root=run_root)
    for doc in docs:
        path = usage_review_dir / f"{doc['review_case_id']}.yaml"
        path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _build_run_index(
    *,
    repo_root: Path,
    output_root: Path,
) -> dict[str, dict[str, Any]]:
    generated_root = output_root / "generated"
    return {
        "investing": {
            "bundle_id": INVESTING_BUNDLE_ID,
            "bundle_path": repo_root / "bundles" / INVESTING_BUNDLE_ID,
            "run_id": "baseline-investing",
            "run_root": generated_root / INVESTING_BUNDLE_ID / "baseline-investing",
            "usage_review_dir": generated_root / INVESTING_BUNDLE_ID / "baseline-investing" / "usage-review",
            "three_layer_review_exists": False,
            "build_payload": None,
            "review_payload": None,
        },
        "engineering": {
            "bundle_id": ENGINEERING_BUNDLE_ID,
            "bundle_path": repo_root / "bundles" / ENGINEERING_BUNDLE_ID,
            "run_id": "baseline-engineering",
            "run_root": generated_root / ENGINEERING_BUNDLE_ID / "baseline-engineering",
            "usage_review_dir": generated_root / ENGINEERING_BUNDLE_ID / "baseline-engineering" / "usage-review",
            "three_layer_review_exists": False,
            "build_payload": None,
            "review_payload": None,
        },
    }


def _select_checks(
    checks: list[RegressionCheck],
    *,
    only: Iterable[str] | None,
    skip: Iterable[str] | None,
) -> list[RegressionCheck]:
    available = {check.check_id for check in checks}
    only_ids = list(only or [])
    skip_ids = set(skip or [])
    unknown_only = [check_id for check_id in only_ids if check_id not in available]
    unknown_skip = [check_id for check_id in skip_ids if check_id not in available]
    if unknown_only or unknown_skip:
        unknown = unknown_only + unknown_skip
        raise ValueError(f"Unknown regression check ids: {', '.join(sorted(set(unknown)))}")

    if only_ids:
        only_set = set(only_ids)
        return [check for check in checks if check.check_id in only_set and check.check_id not in skip_ids]
    return [check for check in checks if check.check_id not in skip_ids]


def _build_subprocess_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_root = str(repo_root / "src")
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_root if not current_pythonpath else f"{src_root}{os.pathsep}{current_pythonpath}"
    )
    return env


def _parse_json_stdout(stdout: str) -> dict[str, Any] | None:
    stdout = stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _tail(text: str, *, max_chars: int = 1200) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _usage_review_docs(
    *,
    bundle_id: str,
    run_root: Path,
) -> list[dict[str, Any]]:
    if bundle_id == INVESTING_BUNDLE_ID:
        return [
            {
                "review_case_id": "baseline-circle-of-competence",
                "generated_run_root": str(run_root),
                "skill_path": str(run_root / "bundle" / "skills" / "circle-of-competence" / "SKILL.md"),
                "input_scenario": {
                    "question": "朋友强烈推荐一支我完全不理解商业模式的热门股票。",
                    "constraint": "我现在只能复述市场情绪，无法解释关键盈利机制。",
                },
                "firing_assessment": {
                    "should_fire": True,
                    "why_this_skill_fired": [
                        "叙事热度高，但理解深度不足。",
                        "用户需要先判断是否超出能力圈。",
                    ],
                },
                "boundary_check": {
                    "status": "pass",
                    "notes": ["场景聚焦在是否应立即行动，而不是完整估值。"],
                },
                "structured_output": {
                    "verdict": "do_not_act_yet",
                    "next_action": "state_knowledge_gap",
                    "confidence": "high",
                },
                "analysis_summary": "先明确自己不知道什么，再决定是否继续研究或拒绝行动。",
                "quality_assessment": {
                    "contract_fit": "strong",
                    "evidence_alignment": ["dotcom-refusal", "google-omission"],
                    "caveats": ["如果用户已经完成一手研究，这个 skill 只应作为前置筛查。"],
                },
            }
        ]
    if bundle_id == ENGINEERING_BUNDLE_ID:
        return [
            {
                "review_case_id": "baseline-postmortem-blameless",
                "generated_run_root": str(run_root),
                "skill_path": str(run_root / "bundle" / "skills" / "postmortem-blameless" / "SKILL.md"),
                "input_scenario": {
                    "incident_summary": "线上变更后接口错误率抬升，群里开始点名某个值班同学负责。",
                    "timeline": "变更审批放宽，告警触发延迟，回滚按钮不可见。",
                    "current_blame_narrative": "先找个人背锅再说。",
                },
                "firing_assessment": {
                    "should_fire": True,
                    "why_this_skill_fired": [
                        "讨论正在滑向归责个人。",
                        "系统因素和时间线还没有被完整重建。",
                    ],
                },
                "boundary_check": {
                    "status": "pass",
                    "notes": ["事故已初步止血，适合进入复盘阶段。"],
                },
                "structured_output": {
                    "verdict": "reframe_to_systems",
                    "next_action": "reconstruct_timeline",
                    "confidence": "high",
                },
                "analysis_summary": "先补时间线和系统诱因，再谈个人动作的上下文。",
                "quality_assessment": {
                    "contract_fit": "strong",
                    "evidence_alignment": ["blameless-db-index-rollout", "incident-timeline-gap"],
                    "caveats": ["如果事故仍未受控，应先执行恢复流程而不是复盘。"],
                },
            }
        ]
    raise ValueError(f"Unsupported bundle id for baseline usage review fixtures: {bundle_id}")

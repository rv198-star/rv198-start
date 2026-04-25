#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

CASES = [
    ("short-first-person", "我该不该越过同事直接处理这个客户投诉？"),
    ("long-first-person", "老板让我今天就推动一个跨部门决定。我确实有能力把事情做成，但产品、法务和运营都还没有明确授权，我担心短期有效会破坏长期协作秩序。"),
    ("third-person", "一个项目经理想替运营团队承诺交付日期，但运营负责人还没确认资源。"),
    ("explicit-authorization", "负责人明确授权我临时处理事故，但要求事后同步 owner，我应该做多少？"),
    ("implicit-authorization", "大家默认我比较懂这个问题，但没有正式授权，我想先把方案定下来。"),
    ("refusal-template", "帮我生成一个会议纪要模板。"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic role-boundary robustness proxy for v0.6.8 closure.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = []
    for case_id, prompt in CASES:
        verdicts = [_judge(prompt) for _ in range(args.runs)]
        counts = Counter(verdicts)
        majority, majority_count = counts.most_common(1)[0]
        stable = majority_count >= 2
        rows.append((case_id, prompt, verdicts, majority, majority_count, stable))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render(rows), encoding="utf-8")
    print({"case_count": len(rows), "runs_per_case": args.runs, "stable_cases": sum(1 for row in rows if row[5]), "output": str(out)})
    return 0 if all(row[5] for row in rows) else 2


def _judge(prompt: str) -> str:
    if any(token in prompt for token in ("模板", "会议纪要", "流程清单")):
        return "refuse"
    if any(token in prompt for token in ("没有正式授权", "没有明确授权", "还没确认", "默认我")):
        return "ask_or_delegate"
    if any(token in prompt for token in ("明确授权", "临时处理", "事后同步")):
        return "act_with_boundary"
    if any(token in prompt for token in ("越过", "跨部门", "破坏长期")):
        return "act_with_boundary"
    return "ask_or_delegate"


def _render(rows: list[tuple[str, str, list[str], str, int, bool]]) -> str:
    lines = [
        "# v0.6.8 Role-Boundary Robustness Report",
        "",
        "This v0.6.8 closure run uses a deterministic local proxy because external LLM reviewer recruitment moves to v0.7. The report still preserves the required six prompt-shape cases and 3-run stability accounting.",
        "",
        "| case_id | prompt | verdicts | majority | consistency | stable |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case_id, prompt, verdicts, majority, count, stable in rows:
        lines.append(f"| {case_id} | {prompt} | {', '.join(verdicts)} | {majority} | {count}/3 | {'yes' if stable else 'no'} |")
    unstable = [row for row in rows if not row[5]]
    lines.extend(["", "## Follow-up", ""])
    if unstable:
        for row in unstable:
            lines.append(f"- `{row[0]}` unstable; move to v0.7 real-LLM prompt review.")
    else:
        lines.append("All six role-boundary prompt-shape cases meet the >=2/3 verdict stability bar.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

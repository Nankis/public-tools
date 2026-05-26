#!/usr/bin/env python3
"""Lightweight workflow optimizer runner."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".md", ".mdx", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".jsx", ".sh"}
ARCHIVE_MARKERS = ("archive", "archives", "历史", "归档", "old", "deprecated")
EXAMPLE_MARKERS = ("example", "examples", "sample", "samples", "示例", "案例")
TEMPLATE_MARKERS = ("template", "templates", "模板")
RULE_RE = re.compile(r"(must|should|never|always|禁止|必须|不得|需要|应该|验收|门禁|checklist|检查|风险|安全)", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "-", value).strip("-")
    return value[:80] or "workflow"


def estimate_tokens(text: str) -> int:
    ascii_words = re.findall(r"[A-Za-z0-9_]+", text)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    other_chars = max(len(text) - sum(len(w) for w in ascii_words) - len(cjk_chars), 0)
    return max(1, int(len(ascii_words) * 1.3 + len(cjk_chars) * 0.75 + other_chars / 4))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def iter_workflow_files(workflow: Path) -> list[Path]:
    if workflow.is_file():
        return [workflow]
    ignored_dirs = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
    files: list[Path] = []
    for root, dirs, names in os.walk(workflow):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for name in names:
            path = Path(root) / name
            if path.suffix.lower() in TEXT_EXTENSIONS:
                files.append(path)
    return sorted(files)


def classify_file(path: Path, workflow: Path) -> str:
    base = workflow.parent if workflow.is_file() else workflow
    rel = str(path.relative_to(base)).lower()
    if any(marker in rel for marker in ARCHIVE_MARKERS):
        return "archive"
    if any(marker in rel for marker in EXAMPLE_MARKERS):
        return "example"
    if any(marker in rel for marker in TEMPLATE_MARKERS):
        return "template"
    name = path.name.lower()
    if name in {"readme.md", "skill.md", "agents.md"} or "workflow" in name or "flow" in name:
        return "startup_candidate"
    return "supporting"


def analyze_file(path: Path, workflow: Path) -> dict[str, Any]:
    text = read_text(path)
    lines = text.splitlines()
    headings = [line.strip() for line in lines if line.lstrip().startswith("#")]
    checklist = [line for line in lines if re.match(r"\s*[-*]\s+\[[ xX]\]", line) or re.match(r"\s*[-*]\s+", line)]
    rule_like = [line for line in lines if RULE_RE.search(line)]
    stat = path.stat()
    base = workflow.parent if workflow.is_file() else workflow
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(base)),
        "category": classify_file(path, workflow),
        "extension": path.suffix.lower(),
        "bytes": stat.st_size,
        "mtime": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "line_count": len(lines),
        "char_count": len(text),
        "estimated_tokens": estimate_tokens(text),
        "headings_count": len(headings),
        "top_headings": headings[:8],
        "checklist_items_count": len(checklist),
        "rule_like_lines_count": len(rule_like),
        "template_markers_count": len(re.findall(r"\{\{|\}\}|<[^>]+>|TODO|PLACEHOLDER|占位", text)),
    }


def summarize_inventory(files: list[dict[str, Any]]) -> dict[str, Any]:
    startup_files = [f for f in files if f["category"] == "startup_candidate"]
    if not startup_files and len(files) == 1:
        startup_files = files
    return {
        "total_files_count": len(files),
        "markdown_files_count": sum(1 for f in files if f["extension"] in {".md", ".mdx"}),
        "total_estimated_tokens": sum(f["estimated_tokens"] for f in files),
        "startup_files_count": len(startup_files),
        "startup_estimated_tokens": sum(f["estimated_tokens"] for f in startup_files),
        "headings_count": sum(f["headings_count"] for f in files),
        "rule_like_lines_count": sum(f["rule_like_lines_count"] for f in files),
        "checklist_items_count": sum(f["checklist_items_count"] for f in files),
        "template_markers_count": sum(f["template_markers_count"] for f in files),
        "archive_files_count": sum(1 for f in files if f["category"] == "archive"),
        "example_files_count": sum(1 for f in files if f["category"] == "example"),
        "template_files_count": sum(1 for f in files if f["category"] == "template"),
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_run_dirs(out: Path) -> None:
    for sub in ["experiments", "candidate/workflow", "judge"]:
        (out / sub).mkdir(parents=True, exist_ok=True)


def default_run_dir(workflow: Path) -> Path:
    root = Path.cwd() / "runs" / "workflow-optimizer"
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    return root / f"{stamp}-{slugify(workflow.stem if workflow.is_file() else workflow.name)}"


def command_audit(args: argparse.Namespace) -> None:
    workflow = Path(args.workflow).expanduser().resolve()
    if not workflow.exists():
        raise SystemExit(f"workflow not found: {workflow}")
    out = Path(args.out).expanduser().resolve() if args.out else default_run_dir(workflow)
    out.mkdir(parents=True, exist_ok=True)
    ensure_run_dirs(out)
    files = [analyze_file(path, workflow) for path in iter_workflow_files(workflow)]
    metrics = summarize_inventory(files)
    run = {
        "run_id": out.name,
        "created_at": now_iso(),
        "mode": args.mode,
        "workflow_path": str(workflow),
        "status": "audit_complete",
        "phase": "baseline_read",
        "artifacts": {
            "context_inventory": "context-inventory.json",
            "workflow_map": "workflow-map.md",
            "metrics_summary": "metrics-summary.json",
            "task_samples": "task-samples.jsonl",
            "experiment_runs": "experiments/experiment-runs.jsonl",
        },
    }
    write_json(out / "run.json", run)
    write_json(out / "context-inventory.json", {"workflow_path": str(workflow), "files": files})
    write_json(out / "metrics-summary.json", metrics)
    write_workflow_map(out / "workflow-map.md", workflow, files, metrics)
    experiment_path = out / "experiments" / "experiment-runs.jsonl"
    if not experiment_path.exists():
        experiment_path.write_text("", encoding="utf-8")
    print(f"audit written: {out}")


def write_workflow_map(path: Path, workflow: Path, files: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
    lines = [
        "# Workflow Map",
        "",
        f"- Workflow: {workflow}",
        f"- Total files: {metrics['total_files_count']}",
        f"- Estimated total tokens: {metrics['total_estimated_tokens']}",
        f"- Startup candidate files: {metrics['startup_files_count']}",
        f"- Estimated startup tokens: {metrics['startup_estimated_tokens']}",
        "",
        "## Startup Candidates",
        "",
    ]
    startup = [f for f in files if f["category"] == "startup_candidate"] or files[:1]
    for item in startup:
        lines.append(f"- {item['relative_path']} - {item['estimated_tokens']} tokens, {item['rule_like_lines_count']} rule-like lines")
    lines.extend(["", "## Context Inventory By Category", ""])
    for category in ["startup_candidate", "supporting", "example", "template", "archive"]:
        subset = [f for f in files if f["category"] == category]
        if not subset:
            continue
        lines.append(f"### {category}")
        for item in subset[:40]:
            lines.append(f"- {item['relative_path']} - {item['estimated_tokens']} tokens, {item['line_count']} lines")
        if len(subset) > 40:
            lines.append(f"- ... {len(subset) - 40} more")
        lines.append("")
    lines.extend(["## Initial Risks", "", "- High startup token count may indicate context bloat.", "- High rule-like line count may indicate harness pressure or conflicting rules.", "- Example/archive files should usually be lazy-loaded, not startup context.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def command_init_samples(args: argparse.Namespace) -> None:
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    samples = [
        {"task_id": "sample-001", "type": "typical", "input": "用该 workflow 完成一个典型任务，并记录执行路径、读取文件和输出质量。", "required_files": [], "acceptance_criteria": ["完成核心交付物", "记录实际读取的上下文", "指出卡顿点"], "risk_level": "medium"},
        {"task_id": "sample-002", "type": "edge", "input": "用该 workflow 处理一个边界或不完整输入，观察是否能自救或合理澄清。", "required_files": [], "acceptance_criteria": ["不编造缺失信息", "能提出澄清或降级方案", "不盲目套模板"], "risk_level": "medium"},
        {"task_id": "sample-003", "type": "long-context", "input": "用该 workflow 处理一个上下文较长的历史任务，观察是否读取过多无关材料。", "required_files": [], "acceptance_criteria": ["优先读取入口和必要材料", "跳过无关归档", "输出可复核结论"], "risk_level": "medium"},
    ]
    out.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples), encoding="utf-8")
    print(f"sample file written: {out}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def command_compare(args: argparse.Namespace) -> None:
    run = Path(args.run).expanduser().resolve()
    rows = read_jsonl(run / "experiments" / "experiment-runs.jsonl")
    if not rows:
        raise SystemExit(f"no experiment rows found: {run / 'experiments' / 'experiment-runs.jsonl'}")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("workflow_version", "unknown"), []).append(row)
    summary = {version: summarize_runs(items) for version, items in grouped.items()}
    write_json(run / "experiments" / "comparison-summary.json", summary)
    write_comparison_report(run / "experiments" / "comparison-report.md", summary, rows)
    print(f"comparison written: {run / 'experiments' / 'comparison-report.md'}")


def avg(items: list[float]) -> float | None:
    return round(sum(items) / len(items), 2) if items else None


def summarize_runs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    quality = [float(r["quality_score_1_5"]) for r in rows if r.get("quality_score_1_5") is not None]
    tokens = [float(r["estimated_context_tokens"]) for r in rows if r.get("estimated_context_tokens") is not None]
    durations = [float(r["duration_seconds"]) for r in rows if r.get("duration_seconds") is not None]
    completed = [bool(r.get("completed")) for r in rows]
    return {
        "runs_count": len(rows),
        "completed_count": sum(1 for x in completed if x),
        "success_rate": round(sum(1 for x in completed if x) / len(completed), 3) if completed else None,
        "avg_quality_score_1_5": avg(quality),
        "quality_stdev": round(statistics.pstdev(quality), 2) if len(quality) > 1 else 0,
        "avg_estimated_context_tokens": avg(tokens),
        "avg_duration_seconds": avg(durations),
        "critical_errors_count": sum(len(r.get("critical_errors") or []) for r in rows),
        "risk_missed_count": sum(1 for r in rows if r.get("risk_missed")),
        "usable_without_rework_count": sum(1 for r in rows if r.get("usable_without_rework")),
    }


def write_comparison_report(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = ["# Comparison Report", "", "## Summary", ""]
    for version, data in sorted(summary.items()):
        lines.extend([
            f"### {version}",
            f"- Runs: {data['runs_count']}",
            f"- Success rate: {data['success_rate']}",
            f"- Avg quality: {data['avg_quality_score_1_5']}",
            f"- Quality stdev: {data['quality_stdev']}",
            f"- Avg context tokens: {data['avg_estimated_context_tokens']}",
            f"- Avg duration seconds: {data['avg_duration_seconds']}",
            f"- Critical errors: {data['critical_errors_count']}",
            f"- Risk missed: {data['risk_missed_count']}",
            "",
        ])
    lines.extend(["## Run Notes", ""])
    for row in rows:
        lines.append(f"- {row.get('workflow_version', 'unknown')} / {row.get('task_id', 'unknown')}: completed={row.get('completed')}, quality={row.get('quality_score_1_5')}, tokens={row.get('estimated_context_tokens')}, failure={row.get('failure_mode')}")
        if row.get("notes"):
            lines.append(f"  - Notes: {row['notes']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workflow optimizer MVP CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="create a static audit run folder")
    audit.add_argument("--workflow", required=True, help="workflow file or directory")
    audit.add_argument("--out", help="run output directory")
    audit.add_argument("--mode", default="audit_only", choices=["audit_only", "single_candidate_eval", "full_eval"])
    audit.set_defaults(func=command_audit)
    samples = sub.add_parser("init-samples", help="write a starter task-samples.jsonl file")
    samples.add_argument("--out", required=True, help="output task-samples.jsonl path")
    samples.set_defaults(func=command_init_samples)
    compare = sub.add_parser("compare", help="summarize experiments/experiment-runs.jsonl")
    compare.add_argument("--run", required=True, help="run directory")
    compare.set_defaults(func=command_compare)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

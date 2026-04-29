"""
sextant tokens — per-stage token and time consumption statistics.

Recording: actual token/time data is written to usage.json by `sextant record-usage`
after each stage completes. When usage.json is absent or a stage is missing, the
command falls back to chars/4 estimation for token counts (no time data).

Token estimation fallback: len(file_text) // 4 (chars/4 approximates tokenizer output).
Use for relative stage comparison, not absolute API billing.
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from cli.parsers import parse_frontmatter


# ── Stage definitions ─────────────────────────────────────────────────

# Path descriptor tuples: (base, relative_path)
# base: "core" = Sextant pkg root/core/
#        "sextant" = project_root/.sextant/
#        "trace" = task trace directory
#        "modules_glob" = project_root/modules/*/EVOLUTION.md (glob)
STAGE_INPUT_RULES: dict[str, list[tuple[str, str]]] = {
    "spec": [
        ("core", "roles/spec.md"),
        ("sextant", "SEXTANT.md"),
        ("sextant", "PROJECT_EVOLUTION_LOG.md"),
        ("modules_glob", ""),
    ],
    "review-spec": [
        ("core", "roles/reviewer.md"),
        ("trace", "spec.md"),
    ],
    "plan": [
        ("core", "roles/planner.md"),
        ("trace", "spec.md"),
        ("sextant", "SEXTANT.md"),
        ("sextant", "hook-registry.json"),
        ("modules_glob", ""),
    ],
    "review-plan": [
        ("core", "roles/reviewer.md"),
        ("trace", "plan.md"),
    ],
    "build": [
        ("core", "roles/builder.md"),
        ("trace", "spec.md"),
        ("trace", "plan.md"),
        ("sextant", "SEXTANT.md"),
        ("sextant", "hook-registry.json"),
    ],
    "review-build": [
        ("core", "roles/reviewer.md"),
        ("trace", "build-summary.md"),
        ("trace", "review-spec.md"),
        ("trace", "review-plan.md"),
        ("trace", "spec.md"),
        ("trace", "plan.md"),
    ],
    "record": [
        ("trace", "build-summary.md"),
        ("trace", "review-build.md"),
        ("trace", "spec.md"),
        ("trace", "plan.md"),
    ],
}

STAGE_OUTPUT_ARTIFACTS: dict[str, str] = {
    "spec": "spec.md",
    "review-spec": "review-spec.md",
    "plan": "plan.md",
    "review-plan": "review-plan.md",
    "build": "build-summary.md",
    "review-build": "review-build.md",
    "record": "record.md",
}

STAGE_ORDER = [
    "spec", "review-spec", "plan", "review-plan",
    "build", "review-build", "record",
]


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class TokenSummary:
    task_id: str
    stage: str
    input_tokens: int
    output_tokens: int
    artifact_exists: bool
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    duration_seconds: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    model: Optional[str] = None
    source: str = "estimated"  # "recorded" | "estimated"


@dataclass
class TokenReport:
    total_tasks: int = 0
    total_tokens: int = 0
    total_duration_seconds: Optional[int] = None
    stage_breakdown: dict = field(default_factory=dict)
    tasks: list = field(default_factory=list)
    since_days: Optional[int] = None
    task_levels: Optional[list[str]] = None
    recorded_tasks: int = 0
    timed_tasks: int = 0


# ── Core estimation ───────────────────────────────────────────────────

def _sextant_root() -> Path:
    """Return the Sextant package root (parent of cli/)."""
    return Path(__file__).parent.parent


def estimate_tokens(path: Path) -> int:
    """Estimate token count from a file: len(text) // 4. Returns 0 if file missing."""
    try:
        return len(path.read_text(encoding="utf-8")) // 4
    except (FileNotFoundError, OSError):
        return 0


def _resolve_input_paths(
    stage: str,
    trace_dir: Path,
    project_root: Path,
) -> list[Path]:
    """Resolve all input file paths for a given stage."""
    sextant_dir = project_root / ".sextant"
    core_dir = _sextant_root() / "core"
    paths: list[Path] = []

    for base, rel in STAGE_INPUT_RULES.get(stage, []):
        if base == "core":
            paths.append(core_dir / rel)
        elif base == "sextant":
            paths.append(sextant_dir / rel)
        elif base == "trace":
            paths.append(trace_dir / rel)
        elif base == "modules_glob":
            paths.extend(sorted(project_root.glob("modules/*/EVOLUTION.md")))

    return paths


# ── usage.json read / write ───────────────────────────────────────────

USAGE_FILENAME = "usage.json"


def read_usage_json(task_dir: Path) -> dict:
    """Read usage.json from a task trace directory. Returns empty dict if absent."""
    path = task_dir / USAGE_FILENAME
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def write_usage_json(
    task_dir: Path,
    stage: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    model: Optional[str] = None,
) -> None:
    """Write or update a single stage entry in usage.json."""
    usage = read_usage_json(task_dir)
    if not usage:
        usage = {"task_id": task_dir.name, "stages": {}}

    # Compute duration from timestamps if not provided
    if duration_seconds is None and started_at and completed_at:
        try:
            t0 = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            duration_seconds = max(0, int((t1 - t0).total_seconds()))
        except (ValueError, TypeError):
            pass

    entry: dict = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "total_tokens": input_tokens + output_tokens,
        "source": "recorded",
    }
    if started_at:
        entry["started_at"] = started_at
    if completed_at:
        entry["completed_at"] = completed_at
    if duration_seconds is not None:
        entry["duration_seconds"] = duration_seconds
    if model:
        entry["model"] = model

    usage.setdefault("stages", {})[stage] = entry

    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / USAGE_FILENAME).write_text(
        json.dumps(usage, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Parsers ───────────────────────────────────────────────────────────

def _parse_completed_at(record_path: Path) -> Optional[datetime]:
    try:
        fm = parse_frontmatter(record_path.read_text(encoding="utf-8"))
        value = fm.get("completed_at", "")
        if not value or not isinstance(value, str):
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_task_level(task_dir: Path) -> Optional[str]:
    for filename in ("spec.md", "plan.md"):
        path = task_dir / filename
        if path.exists():
            try:
                fm = parse_frontmatter(path.read_text(encoding="utf-8"))
                level = fm.get("task_level") or fm.get("level")
                return str(level) if level else None
            except Exception:
                continue
    return None


# ── Collection ────────────────────────────────────────────────────────

def collect_tokens(
    traces_dir: Path,
    since_days: Optional[int] = None,
    task_levels: Optional[list[str]] = None,
) -> list[TokenSummary]:
    """Scan all task trace directories and collect per-stage token summaries.

    Prefers recorded data from usage.json; falls back to file-size estimation.
    """
    if not traces_dir.exists():
        return []

    summaries: list[TokenSummary] = []
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=since_days) if since_days else None
    project_root = traces_dir.parent.parent

    for task_dir in sorted(traces_dir.iterdir()):
        if not task_dir.is_dir() or task_dir.name.startswith("."):
            continue

        record_path = task_dir / "record.md"
        completed_at = _parse_completed_at(record_path) if record_path.exists() else None

        if cutoff and completed_at is None:
            continue
        if cutoff and completed_at and completed_at < cutoff:
            continue

        level = _parse_task_level(task_dir)
        if task_levels and level not in task_levels:
            continue

        usage_data = read_usage_json(task_dir)
        recorded_stages = usage_data.get("stages", {})

        for stage in STAGE_ORDER:
            artifact_name = STAGE_OUTPUT_ARTIFACTS.get(stage, "")
            artifact_path = task_dir / artifact_name if artifact_name else None
            artifact_exists = artifact_path.exists() if artifact_path else False

            if stage in recorded_stages:
                rec = recorded_stages[stage]
                summaries.append(TokenSummary(
                    task_id=task_dir.name,
                    stage=stage,
                    input_tokens=rec.get("input_tokens", 0),
                    output_tokens=rec.get("output_tokens", 0),
                    cache_read_tokens=rec.get("cache_read_tokens", 0),
                    cache_creation_tokens=rec.get("cache_creation_tokens", 0),
                    artifact_exists=artifact_exists,
                    duration_seconds=rec.get("duration_seconds"),
                    started_at=rec.get("started_at"),
                    completed_at=rec.get("completed_at"),
                    model=rec.get("model"),
                    source="recorded",
                ))
            else:
                input_paths = _resolve_input_paths(stage, task_dir, project_root)
                input_tokens = sum(estimate_tokens(p) for p in input_paths)
                output_tokens = estimate_tokens(artifact_path) if artifact_path else 0
                summaries.append(TokenSummary(
                    task_id=task_dir.name,
                    stage=stage,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    artifact_exists=artifact_exists,
                    source="estimated",
                ))

    return summaries


# ── Aggregation ───────────────────────────────────────────────────────

def compute_tokens(summaries: list[TokenSummary], **kwargs) -> TokenReport:
    """Aggregate TokenSummary list into a TokenReport."""
    report = TokenReport(**kwargs)

    if not summaries:
        return report

    task_ids = sorted({s.task_id for s in summaries})
    report.total_tasks = len(task_ids)
    report.total_tokens = sum(s.input_tokens + s.output_tokens for s in summaries)

    # Count tasks with at least one recorded stage and at least one timed stage
    recorded_task_ids = {s.task_id for s in summaries if s.source == "recorded"}
    timed_task_ids = {s.task_id for s in summaries if s.duration_seconds is not None}
    report.recorded_tasks = len(recorded_task_ids)
    report.timed_tasks = len(timed_task_ids)

    # Total duration: sum across all recorded stages with timing
    all_durations = [s.duration_seconds for s in summaries if s.duration_seconds is not None]
    report.total_duration_seconds = sum(all_durations) if all_durations else None

    # Stage breakdown
    stage_data: dict[str, dict] = {
        stage: {
            "input": 0, "output": 0, "cache_read": 0, "cache_creation": 0,
            "duration": 0, "count": 0, "timed_count": 0,
        }
        for stage in STAGE_ORDER
    }
    for s in summaries:
        if s.stage in stage_data:
            d = stage_data[s.stage]
            d["input"] += s.input_tokens
            d["output"] += s.output_tokens
            d["cache_read"] += s.cache_read_tokens
            d["cache_creation"] += s.cache_creation_tokens
            d["count"] += 1
            if s.duration_seconds is not None:
                d["duration"] += s.duration_seconds
                d["timed_count"] += 1

    report.stage_breakdown = {}
    for stage in STAGE_ORDER:
        d = stage_data[stage]
        n = d["count"]
        nt = d["timed_count"]
        report.stage_breakdown[stage] = {
            "avg_input_tokens": d["input"] // n if n else 0,
            "avg_output_tokens": d["output"] // n if n else 0,
            "avg_total_tokens": (d["input"] + d["output"]) // n if n else 0,
            "avg_cache_read_tokens": d["cache_read"] // n if n else 0,
            "avg_cache_creation_tokens": d["cache_creation"] // n if n else 0,
            "total_input_tokens": d["input"],
            "total_output_tokens": d["output"],
            "total_cache_read_tokens": d["cache_read"],
            "total_cache_creation_tokens": d["cache_creation"],
            "avg_duration_seconds": d["duration"] // nt if nt else None,
            "total_duration_seconds": d["duration"] if nt else None,
            "task_count": n,
            "timed_task_count": nt,
        }

    # Per-task breakdown
    for task_id in task_ids:
        task_summaries = {s.stage: s for s in summaries if s.task_id == task_id}
        task_total_tokens = sum(
            s.input_tokens + s.output_tokens for s in task_summaries.values()
        )
        task_durations = [
            s.duration_seconds for s in task_summaries.values()
            if s.duration_seconds is not None
        ]
        task_total_duration = sum(task_durations) if task_durations else None

        stages_out: dict[str, dict] = {}
        for stage in STAGE_ORDER:
            s = task_summaries.get(stage)
            if s:
                stages_out[stage] = {
                    "input": s.input_tokens,
                    "output": s.output_tokens,
                    "cache_read": s.cache_read_tokens,
                    "cache_creation": s.cache_creation_tokens,
                    "exists": s.artifact_exists,
                    "duration_seconds": s.duration_seconds,
                    "started_at": s.started_at,
                    "completed_at": s.completed_at,
                    "model": s.model,
                    "source": s.source,
                }
            else:
                stages_out[stage] = {
                    "input": 0, "output": 0, "cache_read": 0, "cache_creation": 0,
                    "exists": False, "duration_seconds": None,
                    "started_at": None, "completed_at": None,
                    "model": None, "source": "estimated",
                }
        report.tasks.append({
            "task_id": task_id,
            "total_tokens": task_total_tokens,
            "total_duration_seconds": task_total_duration,
            "stages": stages_out,
        })

    return report


# ── Formatting helpers ────────────────────────────────────────────────

def _fmt_duration(seconds: Optional[int]) -> str:
    """Format seconds into human-readable string: 1h 23m 45s / 5m 10s / 45s / —"""
    if seconds is None:
        return "—"
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _fmt_tokens(n: int) -> str:
    return f"{n:,}"


# ── Text formatter ────────────────────────────────────────────────────

def format_tokens(
    report: TokenReport,
    detail_task_id: Optional[str] = None,
) -> str:
    filters: list[str] = []
    if report.since_days:
        filters.append(f"last {report.since_days} days")
    if report.task_levels:
        filters.append(f"levels: {', '.join(report.task_levels)}")
    filter_str = f"  ({', '.join(filters)})" if filters else ""

    if detail_task_id:
        task_data = next((t for t in report.tasks if t["task_id"] == detail_task_id), None)
        if not task_data:
            return f"Task not found in traces: {detail_task_id}"

        dur_str = _fmt_duration(task_data["total_duration_seconds"])
        lines: list[str] = [
            f"Usage breakdown: {detail_task_id}",
            f"  Total tokens:   {task_data['total_tokens']:,}",
            f"  Total time:     {dur_str}",
            "",
            f"  {'Stage':<16} {'Input':>8} {'Output':>8} {'Cache↩':>7} {'Total':>8}  {'Time':>9}  {'Source':<9}  Status",
            f"  {'-'*16} {'-'*8} {'-'*8} {'-'*7} {'-'*8}  {'-'*9}  {'-'*9}  ------",
        ]
        for stage in STAGE_ORDER:
            s = task_data["stages"].get(stage, {})
            total = s.get("input", 0) + s.get("output", 0)
            cache = s.get("cache_read", 0)
            status = "present" if s.get("exists") else "missing"
            dur = _fmt_duration(s.get("duration_seconds"))
            source = s.get("source", "estimated")
            lines.append(
                f"  {stage:<16} {s.get('input', 0):>8,} {s.get('output', 0):>8,} "
                f"{cache:>7,} {total:>8,}  {dur:>9}  {source:<9}  {status}"
            )
        lines += [
            "",
            "  Cache↩ = cache_read_tokens (prompt cache hits).",
            "  Recorded: actual values from sextant record-usage.",
            "  Estimated: chars/4 approximation (no timing available).",
        ]
        return "\n".join(lines)

    # Aggregate view
    total_dur_str = _fmt_duration(report.total_duration_seconds)
    recorded_note = (
        f"recorded: {report.recorded_tasks} · estimated: {report.total_tasks - report.recorded_tasks}"
        if report.total_tasks else ""
    )
    timed_note = f"{report.timed_tasks} tasks" if report.timed_tasks else "no timing data"

    lines = [
        f"Token & Time Statistics{filter_str}",
        f"  Tasks analyzed: {report.total_tasks}",
        f"  Total tokens:   {report.total_tokens:,}"
        + (f"  [{recorded_note}]" if recorded_note else ""),
        f"  Total time:     {total_dur_str}  [{timed_note}]",
        "",
    ]

    if report.total_tasks == 0:
        lines.append("  No task data yet. Complete some tasks to accumulate statistics.")
        lines.append("")
        lines.append("  Tip: run `sextant tokens --detail <task_id>` for a per-stage breakdown.")
        return "\n".join(lines)

    lines += [
        f"  {'Stage':<16} {'Avg Tokens':>10} {'Avg Time':>10}  {'Tasks':>5}  Source",
        f"  {'-'*16} {'-'*10} {'-'*10}  {'-'*5}  ------",
    ]
    for stage in STAGE_ORDER:
        bd = report.stage_breakdown.get(stage, {})
        n = bd.get("task_count", 0)
        if n == 0:
            lines.append(f"  {stage:<16} {'—':>10} {'—':>10}  {'0':>5}")
        else:
            avg_tokens = bd.get("avg_total_tokens", 0)
            avg_dur = _fmt_duration(bd.get("avg_duration_seconds"))
            nt = bd.get("timed_task_count", 0)
            source_label = "recorded" if nt == n else ("mixed" if nt > 0 else "estimated")
            lines.append(
                f"  {stage:<16} {avg_tokens:>10,} {avg_dur:>10}  {n:>5}  {source_label}"
            )

    lines += [
        "",
        "  Avg Tokens = avg(input + output) per task.",
        "  Run `sextant tokens --detail <task_id>` to inspect a specific task.",
    ]
    return "\n".join(lines)


# ── CLI entry points ──────────────────────────────────────────────────

def run_tokens(args) -> int:
    traces_dir = Path(args.traces_dir)

    since_days = getattr(args, "since", None)
    level_filter_str = getattr(args, "task_level", None)
    task_levels = [lv.strip() for lv in level_filter_str.split(",")] if level_filter_str else None
    detail_task_id = getattr(args, "detail", None)
    output_json = getattr(args, "json", False)

    summaries = collect_tokens(traces_dir, since_days=since_days, task_levels=task_levels)
    report = compute_tokens(summaries, since_days=since_days, task_levels=task_levels)

    if output_json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print(format_tokens(report, detail_task_id=detail_task_id))

    return 0


def run_record_usage(args) -> int:
    """Write actual token/time data for one stage into the task's usage.json."""
    traces_dir = Path(args.traces_dir)

    # Resolve task directory
    task_id = getattr(args, "task_id", None)
    if task_id:
        task_dir = traces_dir / task_id
    else:
        # Auto-detect most recently modified trace
        if not traces_dir.exists():
            print("error: traces directory not found and --task-id not specified", file=sys.stderr)
            return 1
        candidates = [
            d for d in traces_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        if not candidates:
            print("error: no task traces found and --task-id not specified", file=sys.stderr)
            return 1
        task_dir = max(candidates, key=lambda d: d.stat().st_mtime)

    if not task_dir.exists():
        print(f"error: task directory not found: {task_dir}", file=sys.stderr)
        return 1

    write_usage_json(
        task_dir=task_dir,
        stage=args.stage,
        input_tokens=args.input_tokens,
        output_tokens=args.output_tokens,
        cache_read_tokens=getattr(args, "cache_read", 0) or 0,
        cache_creation_tokens=getattr(args, "cache_creation", 0) or 0,
        started_at=getattr(args, "started_at", None),
        completed_at=getattr(args, "completed_at", None),
        duration_seconds=getattr(args, "duration", None),
        model=getattr(args, "model", None),
    )

    stage = args.stage
    task_name = task_dir.name
    print(f"Recorded usage for stage '{stage}' in task '{task_name}'.")
    return 0

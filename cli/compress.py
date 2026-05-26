"""
Context compression — reduce memory footprint of completed task traces.

For long-running projects, trace artifacts accumulate. This module compresses
old traces by summarizing them into compact archives while preserving the key
engineering signals:

  - verdicts and review outcomes
  - deletion proposals (reviewer "teeth" signal)
  - scope creep flags
  - knowledge writebacks
  - token/time statistics

Compression targets:
  - traces older than N days (--since)
  - specific task traces (--task-id)
  - all completed traces (--all-completed)

Compressed output: .sextant/compressed/<task-id>.summary.json
"""
from __future__ import annotations
import json
import gzip
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from cli.parsers import parse_frontmatter, parse_section, extract_verdict


@dataclass
class TraceSummary:
    task_id: str
    compressed_at: str = ""
    spec_summary: str = ""
    plan_summary: str = ""
    review_verdicts: dict[str, str] = field(default_factory=dict)  # stage -> verdict
    deletion_proposals: list[str] = field(default_factory=list)
    scope_creep_count: int = 0
    token_stats: Optional[dict] = None
    duration_seconds: Optional[int] = None
    error_count: int = 0
    state: str = "unknown"
    original_file_count: int = 0
    original_size_bytes: int = 0


# ── Compression ───────────────────────────────────────────────────────

def compress_trace(
    trace_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
) -> Optional[TraceSummary]:
    """Compress a single task trace into a summary.

    Returns the summary if successful, None if the trace doesn't exist.
    """
    task_id = trace_dir.name
    if not trace_dir.exists() or not trace_dir.is_dir():
        return None

    # Collect raw stats
    original_size = 0
    original_count = 0
    for f in trace_dir.rglob("*"):
        if f.is_file():
            original_size += f.stat().st_size
            original_count += 1

    summary = TraceSummary(
        task_id=task_id,
        compressed_at=datetime.now(tz=timezone.utc).isoformat(),
        original_file_count=original_count,
        original_size_bytes=original_size,
    )

    # Extract spec summary
    spec_path = trace_dir / "spec.md"
    if spec_path.exists():
        try:
            _, text = _read_file(spec_path)
            fm = parse_frontmatter(text)
            scope = parse_section(text, "scope") or ""
            objective_lines = [
                l.strip("- ").strip()
                for l in scope.splitlines()
                if l.strip().startswith("-") and "<!--" not in l
            ]
            summary.spec_summary = (
                objective_lines[0][:120] if objective_lines
                else fm.get("request_summary", "")[:120]
            )
        except Exception:
            pass

    # Extract plan summary
    plan_path = trace_dir / "plan.md"
    if plan_path.exists():
        try:
            _, text = _read_file(plan_path)
            fm = parse_frontmatter(text)
            summary.plan_summary = str(fm.get("task_level", ""))[:120]
        except Exception:
            pass

    # Extract review verdicts and deletion proposals
    for review_file in ("review-spec.md", "review-plan.md", "review-build.md"):
        path = trace_dir / review_file
        if path.exists():
            try:
                _, text = _read_file(path)
                verdict = extract_verdict(text) or "unknown"
                stage = review_file.replace("review-", "").replace(".md", "")
                summary.review_verdicts[stage] = verdict

                # Collect non-none deletion proposals
                dp = parse_section(text, "deletion_proposals") or ""
                proposals = [
                    l.strip("- ").strip()
                    for l in dp.splitlines()
                    if l.strip().startswith("-")
                    and l.strip("- ").strip().lower() not in ("none", "`none`")
                ]
                summary.deletion_proposals.extend(proposals)
            except Exception:
                pass

    # Extract scope creep count from build summary
    bs_path = trace_dir / "build-summary.md"
    if bs_path.exists():
        try:
            _, text = _read_file(bs_path)
            scf = parse_section(text, "scope_creep_flags") or ""
            items = [l for l in scf.splitlines() if l.strip().startswith("-")]
            summary.scope_creep_count = len(items)
        except Exception:
            pass

    # Extract token stats
    usage_path = trace_dir / "usage.json"
    if usage_path.exists():
        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
            summary.token_stats = _summarize_usage(usage)
        except Exception:
            pass

    # Load state if available
    state_path = Path(".sextant/states") / f"{task_id}.json"
    if state_path.exists():
        try:
            state_data = json.loads(state_path.read_text(encoding="utf-8"))
            summary.state = state_data.get("state", "unknown")
            summary.error_count = state_data.get("error_count", 0)
        except Exception:
            pass

    if dry_run:
        return summary

    # Write compressed summary
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task_id}.summary.json.gz"
    data = json.dumps(asdict(summary), indent=2, default=str)
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        f.write(data)

    return summary


def _read_file(path: Path) -> tuple[dict, str]:
    """Read a trace artifact and return (frontmatter, text)."""
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text), text


def _summarize_usage(usage: dict) -> dict:
    """Extract key token/time metrics from usage.json."""
    stages = usage.get("stages", {})
    total_input = 0
    total_output = 0
    total_duration = 0

    for stage_data in stages.values():
        total_input += stage_data.get("input_tokens", 0)
        total_output += stage_data.get("output_tokens", 0)
        total_duration += stage_data.get("duration_seconds", 0)

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_duration_seconds": total_duration,
        "stage_count": len(stages),
        "stages": list(stages.keys()),
    }


# ── Collection ────────────────────────────────────────────────────────

def find_compressible_traces(
    traces_dir: Path,
    since_days: Optional[int] = None,
    task_id: Optional[str] = None,
    all_completed: bool = False,
) -> list[Path]:
    """Find traces that are candidates for compression."""
    if not traces_dir.exists():
        return []

    if task_id:
        path = traces_dir / task_id
        return [path] if path.exists() else []

    candidates: list[Path] = []
    for d in sorted(traces_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue

        # Check if already compressed
        compressed_path = Path(".sextant/compressed") / f"{d.name}.summary.json.gz"
        if compressed_path.exists():
            continue

        if all_completed:
            # Check if task is complete
            record_path = d / "record.md"
            if record_path.exists():
                candidates.append(d)
            continue

        if since_days is not None:
            record_path = d / "record.md"
            if record_path.exists():
                try:
                    fm, _ = _read_file(record_path)
                    ts = fm.get("completed_at", "")
                    if ts:
                        completed = datetime.fromisoformat(
                            str(ts).replace("Z", "+00:00")
                        )
                        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=since_days)
                        if completed < cutoff:
                            candidates.append(d)
                except Exception:
                    pass

    return candidates


# ── Display ───────────────────────────────────────────────────────────

def format_compression_report(
    summaries: list[TraceSummary],
    total_saved_bytes: int,
    dry_run: bool,
) -> str:
    """Format compression results for display."""
    mode = "DRY-RUN" if dry_run else "COMPRESSED"
    lines = [
        f"Context Compression [{mode}]",
        f"  Traces compressed: {len(summaries)}",
        f"  Space saved:       {_format_bytes(total_saved_bytes)}",
        "",
    ]

    if summaries:
        lines.append(f"  {'Task':<30} {'Verdicts':<25} {'DP':>4} {'Size':>10}")
        lines.append(f"  {'-'*30} {'-'*25} {'-'*4} {'-'*10}")
        for s in summaries:
            verdicts = ", ".join(
                f"{k}={v}" for k, v in s.review_verdicts.items()
            )[:25]
            dp_count = len(s.deletion_proposals)
            size_str = _format_bytes(s.original_size_bytes)
            lines.append(f"  {s.task_id:<30} {verdicts:<25} {dp_count:>4} {size_str:>10}")

    return "\n".join(lines)


def _format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


# ── CLI entry point ───────────────────────────────────────────────────

def run_compress(args) -> int:
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces"))
    since_days = getattr(args, "since", None)
    task_id = getattr(args, "task_id", None)
    all_completed = getattr(args, "all_completed", False)
    dry_run = getattr(args, "dry_run", False)

    output_dir = Path(".sextant/compressed")

    if not since_days and not task_id and not all_completed:
        print("Usage: sextant compress [--since DAYS] [--task-id ID] [--all-completed]")
        print("")
        print("  Compress old task traces into summaries to save context space.")
        print("")
        print("  Options:")
        print("    --since N        Compress tasks older than N days")
        print("    --task-id ID     Compress a specific task")
        print("    --all-completed  Compress all completed tasks")
        print("    --dry-run        Show what would be compressed")
        print("")
        print("  Compressed output: .sextant/compressed/<task-id>.summary.json.gz")
        return 1

    candidates = find_compressible_traces(
        traces_dir=traces_dir,
        since_days=since_days,
        task_id=task_id,
        all_completed=all_completed,
    )

    if not candidates:
        print("  No traces found matching compression criteria.")
        return 0

    print(f"Found {len(candidates)} trace(s) to compress")
    print("")

    summaries: list[TraceSummary] = []
    total_saved = 0

    for trace_dir in candidates:
        summary = compress_trace(trace_dir, output_dir, dry_run=dry_run)
        if summary:
            summaries.append(summary)
            total_saved += summary.original_size_bytes
            if not dry_run:
                print(f"  Compressed: {summary.task_id} ({_format_bytes(summary.original_size_bytes)})")
            else:
                print(f"  (dry-run) Would compress: {summary.task_id}")

    print("")
    print(format_compression_report(summaries, total_saved, dry_run))

    if not dry_run:
        print(f"  Compressed files written to: {output_dir}")
        print(f"  Original traces preserved at: {traces_dir}")

    return 0

"""
sextant metrics — reviewer health metrics aggregated across completed tasks.

DESIGN PRINCIPLE: These metrics exist to detect ritualization drift, not to
grade humans or the LLM. They should trigger curiosity, not punishment.

A drop in "non-empty deletion_proposals ratio" is a signal to investigate
the reviewer prompt or task mix — not a KPI to optimize against. If these
numbers become targets, they stop being useful measurements.

What is measured:
  - non_empty_dp_ratio       : fraction of reviews with non-"none" deletion_proposals
  - reviewer_rejection_ratio : fraction of reviews with verdict changes-requested/rejected
  - consecutive_none_tasks   : fraction of tasks where ALL reviews have "none" proposals
  - conditions_resolution_p50: median time (hours) to resolve approved-with-conditions

What is NOT measured:
  - Whether a proposal was high-quality (semantic judgment — belongs to LLM)
  - Whether a reviewer was "thorough" (same)
  - blindspots_verification_ratio — requires semantic diff analysis; left as manual observation
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from cli.parsers import parse_frontmatter, parse_section, extract_verdict


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class ReviewSummary:
    task_id: str
    stage: str                     # spec | plan | build
    verdict: Optional[str]
    has_non_none_proposals: bool
    completed_at: Optional[datetime]   # from record.md, used for time-based filtering
    conditions_count: int = 0          # number of conditions when approved-with-conditions


@dataclass
class MetricsReport:
    total_reviews: int = 0
    total_tasks: int = 0

    # Core health indicators
    non_empty_dp_ratio: Optional[float] = None        # "reviewer has teeth"
    reviewer_rejection_ratio: Optional[float] = None  # "reviewer drives iteration"
    consecutive_none_tasks: Optional[float] = None    # "ritual drift signal"

    # Breakdown by verdict
    verdict_counts: dict[str, int] = field(default_factory=dict)

    # Metadata
    since_days: Optional[int] = None
    task_levels: Optional[list[str]] = None


# ── Parsers ───────────────────────────────────────────────────────────

def _parse_completed_at(record_path: Path) -> Optional[datetime]:
    """Extract completed_at timestamp from a record.md."""
    try:
        text = record_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        value = fm.get("completed_at", "")
        if not value or not isinstance(value, str):
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_task_level(spec_path: Path) -> Optional[str]:
    """Extract task_level from spec.md or plan.md."""
    try:
        text = spec_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        level = fm.get("task_level") or fm.get("level")
        return str(level) if level else None
    except Exception:
        return None


def _parse_review(review_path: Path) -> Optional[ReviewSummary]:
    """Parse a review-*.md into a ReviewSummary."""
    try:
        text = review_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        stage = str(fm.get("stage", "unknown"))
        verdict = extract_verdict(text)

        # Check deletion_proposals
        dp_section = parse_section(text, "deletion_proposals")
        has_non_none = False
        if dp_section:
            content = dp_section.strip()
            has_non_none = content.lower() not in ("none", "`none`", "")

        # Count conditions
        conditions_section = parse_section(text, "conditions") or ""
        conditions_count = len([
            ln for ln in conditions_section.splitlines()
            if ln.strip().startswith("-") and "[]" not in ln
        ])

        # Derive task_id from path
        task_id = review_path.parent.name

        return ReviewSummary(
            task_id=task_id,
            stage=stage,
            verdict=verdict,
            has_non_none_proposals=has_non_none,
            completed_at=None,   # filled later from record.md
            conditions_count=conditions_count,
        )
    except Exception:
        return None


# ── Aggregation ───────────────────────────────────────────────────────

def collect_reviews(
    traces_dir: Path,
    since_days: Optional[int] = None,
    task_levels: Optional[list[str]] = None,
) -> list[ReviewSummary]:
    """Scan all task trace directories and collect review summaries."""
    if not traces_dir.exists():
        return []

    reviews: list[ReviewSummary] = []
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=since_days) if since_days else None

    for task_dir in sorted(traces_dir.iterdir()):
        if not task_dir.is_dir():
            continue

        # Filter by task_level if requested
        if task_levels:
            spec_path = task_dir / "spec.md"
            plan_path = task_dir / "plan.md"
            level = None
            if spec_path.exists():
                level = _parse_task_level(spec_path)
            elif plan_path.exists():
                level = _parse_task_level(plan_path)
            if level and level not in task_levels:
                continue

        # Get completion time for date filtering
        record_path = task_dir / "record.md"
        completed_at = _parse_completed_at(record_path) if record_path.exists() else None

        if cutoff and completed_at and completed_at < cutoff:
            continue

        for review_file in ("review-spec.md", "review-plan.md", "review-build.md"):
            path = task_dir / review_file
            if path.exists():
                summary = _parse_review(path)
                if summary:
                    summary.completed_at = completed_at
                    reviews.append(summary)

    return reviews


def compute_metrics(reviews: list[ReviewSummary], **kwargs) -> MetricsReport:
    """Aggregate a list of ReviewSummary into a MetricsReport."""
    report = MetricsReport(**kwargs)
    report.total_reviews = len(reviews)

    if not reviews:
        return report

    # Unique task IDs
    task_ids = sorted({r.task_id for r in reviews})
    report.total_tasks = len(task_ids)

    # non_empty_dp_ratio
    non_none_count = sum(1 for r in reviews if r.has_non_none_proposals)
    report.non_empty_dp_ratio = round(non_none_count / len(reviews), 3)

    # reviewer_rejection_ratio
    rejections = sum(
        1 for r in reviews
        if r.verdict and r.verdict.lower() in ("changes-requested", "rejected")
    )
    report.reviewer_rejection_ratio = round(rejections / len(reviews), 3)

    # consecutive_none_tasks: fraction of tasks where ALL reviews have "none" proposals
    all_none_tasks = 0
    for task_id in task_ids:
        task_reviews = [r for r in reviews if r.task_id == task_id]
        if task_reviews and all(not r.has_non_none_proposals for r in task_reviews):
            all_none_tasks += 1
    report.consecutive_none_tasks = round(all_none_tasks / len(task_ids), 3)

    # verdict distribution
    for r in reviews:
        v = r.verdict or "unknown"
        report.verdict_counts[v] = report.verdict_counts.get(v, 0) + 1

    return report


# ── Text formatter ────────────────────────────────────────────────────

def format_metrics(report: MetricsReport) -> str:
    lines: list[str] = []

    filters: list[str] = []
    if report.since_days:
        filters.append(f"last {report.since_days} days")
    if report.task_levels:
        filters.append(f"levels: {', '.join(report.task_levels)}")
    filter_str = f"  ({', '.join(filters)})" if filters else ""

    lines.append(f"Reviewer Health Metrics{filter_str}")
    lines.append(f"  Tasks analyzed:   {report.total_tasks}")
    lines.append(f"  Reviews analyzed: {report.total_reviews}")
    lines.append("")

    if report.total_reviews == 0:
        lines.append("  No review data yet. Run some tasks to accumulate metrics.")
        lines.append("")
        lines.append("  Tip: metrics are only meaningful after ~10+ completed tasks.")
        return "\n".join(lines)

    def pct(ratio: Optional[float]) -> str:
        if ratio is None:
            return "n/a"
        return f"{ratio * 100:.1f}%"

    lines.append("  Core health indicators:")
    lines.append(f"    non-empty deletion_proposals ratio: {pct(report.non_empty_dp_ratio)}")
    lines.append(f"      (signal: reviewer retains 'teeth'; watch if this drops below 30%)")
    lines.append(f"    reviewer rejection ratio:           {pct(report.reviewer_rejection_ratio)}")
    lines.append(f"      (signal: reviewer drives real iteration; very low = rubber stamp)")
    lines.append(f"    tasks where ALL reviews have 'none': {pct(report.consecutive_none_tasks)}")
    lines.append(f"      (signal: ritual drift early warning; investigate if above 50%)")
    lines.append("")

    if report.verdict_counts:
        lines.append("  Verdict distribution:")
        for v, count in sorted(report.verdict_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {v:<30} {count:>4}")
    lines.append("")
    lines.append("  Note: these metrics detect drift, not grade quality.")
    lines.append("  A number outside the range above is a signal to investigate,")
    lines.append("  not a score to report. See docs/metrics.md for interpretation.")

    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────

def run_metrics(args) -> int:
    traces_dir = Path(args.traces_dir)

    since_days = getattr(args, "since", None)
    level_filter_str = getattr(args, "task_level", None)
    task_levels = [l.strip() for l in level_filter_str.split(",")] if level_filter_str else None
    output_json = getattr(args, "json", False)

    reviews = collect_reviews(traces_dir, since_days=since_days, task_levels=task_levels)
    report = compute_metrics(
        reviews,
        since_days=since_days,
        task_levels=task_levels,
    )

    if output_json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print(format_metrics(report))

    return 0

"""
sextant status — read-only snapshot of a task's trace state.

Scans .sextant/traces/<task_id>/ and reports:
  - current stage (inferred from artifact existence + verdicts)
  - each artifact's version and reviewer verdict
  - pending gate
  - rollback markers (version > 1)
  - bypass markers (forced_level: true)

This command is intentionally read-only. It does not modify any trace files,
trigger LLM calls, or re-run gate checks.
"""
from __future__ import annotations
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from cli.parsers import parse_frontmatter, parse_section, extract_verdict, read_artifact


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class ArtifactInfo:
    name: str
    exists: bool
    version: Optional[int] = None
    verdict: Optional[str] = None         # review artifacts only
    scope_creep_count: Optional[int] = None  # build-summary only
    is_rollback: bool = False              # version > 1


@dataclass
class TaskStatus:
    task_id: str
    traces_dir: str
    level: Optional[str] = None
    forced: bool = False
    override_reason: str = ""
    current_stage: str = "unknown"
    pending_gate: Optional[str] = None
    artifacts: list[ArtifactInfo] = field(default_factory=list)
    rollback_markers: list[str] = field(default_factory=list)
    bypass_markers: list[str] = field(default_factory=list)
    is_complete: bool = False


# ── Artifact sequence ─────────────────────────────────────────────────

ARTIFACT_SEQUENCE = [
    "spec.md",
    "review-spec.md",
    "plan.md",
    "review-plan.md",
    "build-summary.md",
    "review-build.md",
    "record.md",
]


# ── Stage inference ───────────────────────────────────────────────────

def _is_approved(verdict: Optional[str]) -> bool:
    if verdict is None:
        return False
    return verdict.lower().strip() in ("approved", "approved-with-conditions")


def infer_stage(artifacts: list[ArtifactInfo]) -> tuple[str, Optional[str]]:
    """Return (stage_label, pending_gate_description | None).

    Stage is inferred purely from which files exist and their verdicts.
    No LLM involvement — deterministic logic only.
    """
    by_name = {a.name: a for a in artifacts}

    def exists(name: str) -> bool:
        return by_name.get(name, ArtifactInfo(name, False)).exists

    def verdict(name: str) -> Optional[str]:
        a = by_name.get(name)
        return a.verdict if a and a.exists else None

    def scope_creep(name: str) -> int:
        a = by_name.get(name)
        return a.scope_creep_count or 0 if a and a.exists else 0

    if not exists("spec.md"):
        return "Pre-Spec", "not started — run /sextant-spec"

    if not exists("review-spec.md"):
        return "Spec", "Gate 1 pending (run /sextant-review --stage spec)"

    if not _is_approved(verdict("review-spec.md")):
        return "Spec (awaiting review approval)", f"Gate 1 pending (review-spec verdict: {verdict('review-spec.md')})"

    # Gate 1 passed
    if not exists("plan.md"):
        return "Plan", None  # waiting for /sextant-plan

    if not exists("review-plan.md"):
        return "Plan", "Gate 2 pending (run /sextant-review --stage plan)"

    if not _is_approved(verdict("review-plan.md")):
        return "Plan (awaiting review approval)", f"Gate 2 pending (review-plan verdict: {verdict('review-plan.md')})"

    # Gate 2 passed
    if not exists("build-summary.md"):
        return "Build", None  # waiting for /sextant-build

    if scope_creep("build-summary.md") > 0:
        count = scope_creep("build-summary.md")
        return "Build (scope creep)", f"Gate 3 blocked — {count} unresolved scope_creep_flag(s)"

    # Gate 3 passed
    if not exists("review-build.md"):
        return "Verify", "Gate 4 pending (run /sextant-verify)"

    if not _is_approved(verdict("review-build.md")):
        return "Verify (awaiting review approval)", f"Gate 4 pending (review-build verdict: {verdict('review-build.md')})"

    # Gate 4 passed
    if not exists("record.md"):
        return "Record", None  # waiting for /sextant-record

    return "Complete", None


# ── Artifact readers ──────────────────────────────────────────────────

def _read_spec(path: Path) -> ArtifactInfo:
    fm, _ = read_artifact(path)
    version = fm.get("spec_version", 1)
    return ArtifactInfo(
        name="spec.md",
        exists=True,
        version=int(version) if isinstance(version, int) else 1,
        is_rollback=isinstance(version, int) and version > 1,
    )


def _read_review(path: Path, stage: str) -> ArtifactInfo:
    fm, text = read_artifact(path)
    version = fm.get("review_version", 1)
    return ArtifactInfo(
        name=f"review-{stage}.md",
        exists=True,
        version=int(version) if isinstance(version, int) else 1,
        verdict=extract_verdict(text),
        is_rollback=isinstance(version, int) and version > 1,
    )


def _read_plan(path: Path) -> ArtifactInfo:
    fm, _ = read_artifact(path)
    version = fm.get("plan_version", 1)
    return ArtifactInfo(
        name="plan.md",
        exists=True,
        version=int(version) if isinstance(version, int) else 1,
        is_rollback=isinstance(version, int) and version > 1,
    )


def _read_build_summary(path: Path) -> ArtifactInfo:
    _, text = read_artifact(path)
    section = parse_section(text, "scope_creep_flags")
    count = 0
    if section and section.strip().lower() not in ("none", "", "[]"):
        items = [ln.strip() for ln in section.splitlines() if ln.strip().startswith("-")]
        count = len(items)
    return ArtifactInfo(
        name="build-summary.md",
        exists=True,
        scope_creep_count=count,
    )


def _read_record(path: Path) -> ArtifactInfo:
    fm, _ = read_artifact(path)
    version = fm.get("record_version", 1)
    return ArtifactInfo(
        name="record.md",
        exists=True,
        version=int(version) if isinstance(version, int) else 1,
        is_rollback=isinstance(version, int) and version > 1,
    )


_READERS = {
    "spec.md": _read_spec,
    "review-spec.md": lambda p: _read_review(p, "spec"),
    "plan.md": _read_plan,
    "review-plan.md": lambda p: _read_review(p, "plan"),
    "build-summary.md": _read_build_summary,
    "review-build.md": lambda p: _read_review(p, "build"),
    "record.md": _read_record,
}


# ── Core loader ───────────────────────────────────────────────────────

def load_task_status(task_id: str, traces_dir: Path) -> TaskStatus:
    """Load and return a TaskStatus for the given task_id.

    Reads from traces_dir/<task_id>/. Pure read — no side effects.
    """
    status = TaskStatus(task_id=task_id, traces_dir=str(traces_dir))
    trace_path = traces_dir / task_id

    if not trace_path.exists():
        status.current_stage = "Trace directory not found"
        return status

    # Load all artifacts in canonical order
    for name in ARTIFACT_SEQUENCE:
        path = trace_path / name
        if path.exists():
            status.artifacts.append(_READERS[name](path))
        else:
            status.artifacts.append(ArtifactInfo(name=name, exists=False))

    # Extract task metadata from spec.md
    spec_path = trace_path / "spec.md"
    if spec_path.exists():
        fm = parse_frontmatter(spec_path.read_text(encoding="utf-8"))
        status.level = str(fm.get("task_level") or fm.get("level") or "")
        status.forced = bool(fm.get("forced_level", False))
        status.override_reason = str(fm.get("override_reason", "") or "")

    # Infer stage
    status.current_stage, status.pending_gate = infer_stage(status.artifacts)
    status.is_complete = status.current_stage == "Complete"

    # Collect rollback markers
    for a in status.artifacts:
        if a.is_rollback:
            status.rollback_markers.append(f"{a.name} (v{a.version})")

    # Collect bypass markers
    if status.forced:
        suffix = f" — {status.override_reason}" if status.override_reason else ""
        status.bypass_markers.append(f"forced_level=true{suffix}")

    return status


# ── Text formatter ────────────────────────────────────────────────────

_OK = "\u2713"   # ✓
_MISSING = "\u00b7"  # ·


def _artifact_line(a: ArtifactInfo) -> str:
    if not a.exists:
        return f"  {_MISSING} {a.name:<28} \u2014"
    cols = [f"  {_OK} {a.name:<28}"]
    if a.version is not None:
        cols.append(f"v{a.version}")
    if a.verdict is not None:
        cols.append(f"reviewer: {a.verdict}")
    if a.scope_creep_count is not None:
        cols.append(f"scope_creep_flags: {a.scope_creep_count}")
    return "  ".join(cols)


def format_status(status: TaskStatus) -> str:
    level = status.level or "unknown"
    forced_str = "yes" if status.forced else "no"
    lines = [
        f"Task:    {status.task_id}",
        f"Level:   {level}  (forced: {forced_str})",
        f"Stage:   {status.current_stage}",
        "Artifacts:",
        *(_artifact_line(a) for a in status.artifacts),
        f"Pending gate:     {status.pending_gate or ('none \u2014 task complete' if status.is_complete else 'none')}",
        f"Rollback markers: {', '.join(status.rollback_markers) or 'none'}",
        f"Bypass markers:   {', '.join(status.bypass_markers) or 'none'}",
    ]
    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────

def run_status(args) -> int:
    traces_dir = Path(args.traces_dir)

    task_id = getattr(args, "task_id", None)
    if not task_id:
        if not traces_dir.exists():
            print(f"error: traces directory not found: {traces_dir}", file=sys.stderr)
            return 1
        candidates = sorted(
            [d for d in traces_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("error: no task traces found", file=sys.stderr)
            return 1
        task_id = candidates[0].name

    status = load_task_status(task_id, traces_dir)

    if getattr(args, "json", False):
        print(json.dumps(asdict(status), indent=2))
    else:
        print(format_status(status))

    return 0

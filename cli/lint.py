"""
sextant lint — minimum-trust structure validation for trace artifacts.

DESIGN CONSTRAINT: This linter validates minimum-trust structure only.
It does NOT assess whether a review is deep, whether a deletion proposal
is high-quality, or whether a plan is elegant. Such judgments belong to
the reviewer role (LLM), not to this tool. Resist any temptation to add
"semantic quality" checks — that turns this into a pseudo-AI and its
complexity will backfire.

Exit codes:
  0 — no errors (warnings are OK)
  1 — one or more errors
"""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cli.parsers import parse_frontmatter, parse_section, extract_verdict, read_artifact
from cli.schema import (
    VERDICT_VALUES,
    PLACEHOLDER_PATTERNS,
    TRACE_FILE_WHITELIST,
    SpecFrontmatterFields,
    PlanFrontmatterFields,
    ReviewFrontmatterFields,
    RecordFrontmatterFields,
    BuildSummaryRequiredSections,
    ReviewRequiredSections,
)


# ── Issue dataclass ───────────────────────────────────────────────────

@dataclass
class Issue:
    file: str
    level: str    # "error" | "warning"
    message: str

    def __str__(self) -> str:
        symbol = "\u2717" if self.level == "error" else "!"
        return f"  {symbol} {self.file}: {self.message}"


# ── Low-level check helpers ───────────────────────────────────────────

def _check_frontmatter_fields(
    name: str,
    fm: dict[str, Any],
    fields: list[tuple[str, type, bool]],
) -> list[Issue]:
    """Verify that required frontmatter fields exist and have correct types."""
    issues: list[Issue] = []
    for field_name, expected_type, allow_empty in fields:
        if field_name not in fm:
            issues.append(Issue(name, "error",
                                f"required frontmatter field '{field_name}' missing"))
            continue
        value = fm[field_name]
        if not isinstance(value, expected_type):
            issues.append(Issue(name, "error",
                                f"field '{field_name}' must be {expected_type.__name__}, "
                                f"got {type(value).__name__}: {value!r}"))
            continue
        if not allow_empty and isinstance(value, str) and not value.strip():
            issues.append(Issue(name, "error",
                                f"required field '{field_name}' is empty"))
    return issues


def _check_positive_int_version(name: str, fm: dict[str, Any], version_field: str) -> list[Issue]:
    """Verify a *_version field is a positive integer."""
    issues: list[Issue] = []
    value = fm.get(version_field)
    if value is not None and not (isinstance(value, int) and value >= 1):
        issues.append(Issue(name, "error",
                            f"'{version_field}' must be a positive integer, got: {value!r}"))
    return issues


def _check_deletion_proposals(name: str, text: str) -> list[Issue]:
    """
    Verify deletion_proposals section:
    - section must exist (contract violation if missing)
    - if content is 'none' (literal), that's valid
    - if content is anything else, must be a non-empty bullet list
      with no placeholder items
    """
    issues: list[Issue] = []
    section = parse_section(text, "deletion_proposals")

    if section is None:
        issues.append(Issue(name, "error",
                            "deletion_proposals section missing (contract violation, not formatting)"))
        return issues

    content = section.strip()

    # Valid literal "none"
    if content.lower() == "none" or content.lower() == "`none`":
        return issues

    # Must be a bullet list
    bullets = [ln.strip() for ln in content.splitlines() if ln.strip().startswith("-")]
    if not bullets:
        issues.append(Issue(name, "error",
                            "deletion_proposals is non-empty but contains no bullet items "
                            "(use 'none' if there are no proposals)"))
        return issues

    # Check for placeholder bullets
    for bullet in bullets:
        # Strip leading "- " for text check
        text_part = bullet.lstrip("-").strip().strip("`").lower()
        if text_part in PLACEHOLDER_PATTERNS or text_part.startswith("<!--"):
            issues.append(Issue(name, "error",
                                f"deletion_proposals contains placeholder item: {bullet!r}"))

    return issues


def _check_verdict(name: str, text: str) -> list[Issue]:
    """Verify the verdict section exists and contains a valid value."""
    issues: list[Issue] = []
    verdict = extract_verdict(text)

    if verdict is None:
        issues.append(Issue(name, "error", "verdict section missing or unreadable"))
        return issues

    # Detect template residue: multiple pipe-separated values
    raw_section = parse_section(text, "verdict") or ""
    if "|" in raw_section and raw_section.count("|") >= 2:
        issues.append(Issue(name, "error",
                            "verdict field appears to be unfilled template placeholder "
                            "(contains multiple pipe-separated values)"))
        return issues

    if verdict.lower() not in VERDICT_VALUES:
        issues.append(Issue(name, "error",
                            f"verdict '{verdict}' is not a valid value; "
                            f"must be one of: {', '.join(sorted(VERDICT_VALUES))}"))
    return issues


# ── Per-artifact check functions ──────────────────────────────────────

def _lint_spec(path: Path) -> list[Issue]:
    name = path.name
    fm, _ = read_artifact(path)
    issues = _check_frontmatter_fields(name, fm, SpecFrontmatterFields)
    issues += _check_positive_int_version(name, fm, "spec_version")

    # forced_level rule: if true, override_reason must be non-empty
    if fm.get("forced_level") is True:
        reason = fm.get("override_reason", "")
        if not (isinstance(reason, str) and reason.strip()):
            issues.append(Issue(name, "error",
                                "forced_level=true but override_reason is empty or missing"))
    return issues


def _lint_review(path: Path, stage: str) -> list[Issue]:
    name = path.name
    fm, text = read_artifact(path)
    issues = _check_frontmatter_fields(name, fm, ReviewFrontmatterFields)
    issues += _check_positive_int_version(name, fm, "review_version")

    # Validate stage field matches expected value
    actual_stage = fm.get("stage", "")
    if isinstance(actual_stage, str) and actual_stage and actual_stage != stage:
        # Only warn — stage mismatch could be a typo but shouldn't block
        issues.append(Issue(name, "warning",
                            f"stage field is '{actual_stage}' but filename suggests '{stage}'"))

    issues += _check_deletion_proposals(name, text)
    issues += _check_verdict(name, text)
    return issues


def _lint_plan(path: Path) -> list[Issue]:
    name = path.name
    fm, text = read_artifact(path)
    issues = _check_frontmatter_fields(name, fm, PlanFrontmatterFields)
    issues += _check_positive_int_version(name, fm, "plan_version")

    # task_level value check
    level = fm.get("task_level", "")
    if level and str(level) not in ("L0", "L1", "L2"):
        issues.append(Issue(name, "error",
                            f"task_level '{level}' is not valid; must be L0, L1, or L2"))
    return issues


def _lint_build_summary(path: Path) -> list[Issue]:
    name = path.name
    _, text = read_artifact(path)
    issues: list[Issue] = []

    for section_name in BuildSummaryRequiredSections:
        section = parse_section(text, section_name)
        if section is None:
            issues.append(Issue(name, "error",
                                f"required section '{section_name}' missing"))
            continue
        # scope_creep_flags with items → warning only (not blocking by itself)
        if section_name == "scope_creep_flags":
            content = section.strip()
            if content.lower() not in ("none", "[]", ""):
                bullets = [ln for ln in content.splitlines() if ln.strip().startswith("-")]
                if bullets:
                    issues.append(Issue(name, "warning",
                                        f"scope_creep_flags contains {len(bullets)} unresolved item(s)"))
    return issues


def _lint_record(path: Path) -> list[Issue]:
    name = path.name
    fm, text = read_artifact(path)
    issues = _check_frontmatter_fields(name, fm, RecordFrontmatterFields)
    issues += _check_positive_int_version(name, fm, "record_version")

    # task_level value check
    level = fm.get("task_level", "")
    if level and str(level) not in ("L0", "L1", "L2"):
        issues.append(Issue(name, "error",
                            f"task_level '{level}' is not valid; must be L0, L1, or L2"))

    # Must have either knowledge_writebacks or skip_reason (not both, not neither)
    has_writebacks = parse_section(text, "knowledge_writebacks") is not None
    has_skip_reason = parse_section(text, "skip_reason") is not None

    if not has_writebacks and not has_skip_reason:
        issues.append(Issue(name, "error",
                            "record must contain either 'knowledge_writebacks' or "
                            "'skip_reason' section — neither found"))
    return issues


def _lint_directory(trace_path: Path) -> list[Issue]:
    """Warn about files in the trace directory that aren't in the whitelist."""
    issues: list[Issue] = []
    for f in trace_path.iterdir():
        if f.is_file() and f.name not in TRACE_FILE_WHITELIST:
            issues.append(Issue(f.name, "warning",
                                f"unexpected file in trace directory (not in whitelist)"))
    return issues


# ── Per-file dispatcher ───────────────────────────────────────────────

_ARTIFACT_LINTERS = {
    "spec.md": _lint_spec,
    "review-spec.md": lambda p: _lint_review(p, "spec"),
    "plan.md": _lint_plan,
    "review-plan.md": lambda p: _lint_review(p, "plan"),
    "build-summary.md": _lint_build_summary,
    "review-build.md": lambda p: _lint_review(p, "build"),
    "record.md": _lint_record,
}


# ── Main lint runner ──────────────────────────────────────────────────

def lint_task(task_id: str, traces_dir: Path) -> tuple[list[Issue], int]:
    """Run all lint checks for a task. Returns (issues, exit_code).

    exit_code 0 = clean or warnings only; 1 = one or more errors.
    """
    trace_path = traces_dir / task_id
    if not trace_path.exists():
        return [Issue(task_id, "error", "trace directory not found")], 1

    all_issues: list[Issue] = []

    # Directory structure check
    all_issues += _lint_directory(trace_path)

    # Per-artifact checks (only for files that exist)
    for name, linter in _ARTIFACT_LINTERS.items():
        path = trace_path / name
        if path.exists():
            all_issues += linter(path)

    error_count = sum(1 for i in all_issues if i.level == "error")
    return all_issues, (1 if error_count > 0 else 0)


# ── Formatter ─────────────────────────────────────────────────────────

def format_lint_report(task_id: str, issues: list[Issue], exit_code: int) -> str:
    error_count = sum(1 for i in issues if i.level == "error")
    warning_count = sum(1 for i in issues if i.level == "warning")

    lines: list[str] = []

    if not issues:
        lines.append(f"  \u2713 {task_id}: all checks passed")
    else:
        # Group by file for readability
        by_file: dict[str, list[Issue]] = {}
        for issue in issues:
            by_file.setdefault(issue.file, []).append(issue)

        # Show errors first, then warnings
        for level in ("error", "warning"):
            for file_name, file_issues in by_file.items():
                for issue in file_issues:
                    if issue.level == level:
                        lines.append(str(issue))

    lines.append("")
    parts = []
    if error_count:
        parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
    if warning_count:
        parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
    if not parts:
        parts = ["0 errors, 0 warnings"]
    lines.append("  " + ", ".join(parts))

    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────

def run_lint(args) -> int:
    if getattr(args, "skip_lint", False):
        print("warning: --skip-lint used (developer debug mode only)", file=sys.stderr)
        return 0

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

    issues, exit_code = lint_task(task_id, traces_dir)
    print(format_lint_report(task_id, issues, exit_code))
    return exit_code

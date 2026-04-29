"""
Minimum-trust structural schema for Sextant trace artifacts.

Defines only what a linter can mechanically verify:
  - which frontmatter fields are required and their expected types
  - which markdown sections are mandatory
  - allowed verdict values
  - placeholder string patterns to reject

Does NOT define quality requirements — whether a review is deep,
a proposal is useful, or a plan is elegant. Those judgments belong
to the reviewer role (LLM).
"""
from __future__ import annotations
from typing import Any


# Allowed verdict values (exact lowercase match after stripping)
VERDICT_VALUES: frozenset[str] = frozenset({
    "approved",
    "approved-with-conditions",
    "changes-requested",
    "rejected",
})

# Strings that indicate a placeholder — not allowed in non-"none" deletion_proposals bullets
PLACEHOLDER_PATTERNS: frozenset[str] = frozenset({
    "todo",
    "tbd",
    "n/a",
    "n/a.",
    "pending",
    "待补充",
    "暂无",
    "none yet",
    "placeholder",
})

# Allowed file names in a trace directory
TRACE_FILE_WHITELIST: frozenset[str] = frozenset({
    "spec.md",
    "review-spec.md",
    "plan.md",
    "review-plan.md",
    "build-summary.md",
    "review-build.md",
    "rca.md",
    "record.md",
    "usage.json",
})

ARTIFACT_SEQUENCE: list[str] = [
    "spec.md",
    "review-spec.md",
    "plan.md",
    "review-plan.md",
    "build-summary.md",
    "review-build.md",
    "record.md",
]


# ── Per-artifact field requirements ──────────────────────────────────

# Each entry: (field_name, expected_python_type, allow_empty)
SpecFrontmatterFields: list[tuple[str, type, bool]] = [
    ("task_id", str, False),
    ("spec_version", int, False),
    ("forced_level", bool, True),   # optional, defaults to false
]

PlanFrontmatterFields: list[tuple[str, type, bool]] = [
    ("task_id", str, False),
    ("spec_ref", str, False),
    ("plan_version", int, False),
    ("task_level", str, False),
]

ReviewFrontmatterFields: list[tuple[str, type, bool]] = [
    ("stage", str, False),
    ("reviewed_artifact_ref", str, False),
    ("reviewer_session_id", str, False),
    ("review_version", int, False),
]

RecordFrontmatterFields: list[tuple[str, type, bool]] = [
    ("task_id", str, False),
    ("completed_at", str, False),
    ("task_level", str, False),
    ("record_version", int, False),
]

# Build-summary uses markdown sections only (no required frontmatter)
BuildSummaryRequiredSections: list[str] = [
    "spec_ref",
    "plan_ref",
    "changes_summary",
    "footprint_delta",
    "scope_creep_flags",
    "hooks_passed",
]

# Review mandatory sections
ReviewRequiredSections: list[str] = [
    "deletion_proposals",
    "verdict",
]

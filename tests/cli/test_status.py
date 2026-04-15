"""Tests for sextant status command."""
from __future__ import annotations
from pathlib import Path

import pytest

from cli.parsers import extract_verdict, parse_frontmatter, parse_section
from cli.status import format_status, load_task_status


# ── Fixture helpers ───────────────────────────────────────────────────

def write_spec(
    trace: Path,
    *,
    version: int = 1,
    forced: bool = False,
    reason: str = "",
    level: str = "L1",
) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "spec.md").write_text(
        f"---\n"
        f"task_id: test-task\n"
        f"task_level: {level}\n"
        f"spec_version: {version}\n"
        f"forced_level: {str(forced).lower()}\n"
        f'override_reason: "{reason}"\n'
        f"---\n\n## scope\n\nIn scope: test\n"
    )


def write_review(trace: Path, stage: str, verdict: str, version: int = 1) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / f"review-{stage}.md").write_text(
        f"---\n"
        f"stage: {stage}\n"
        f"reviewed_artifact_ref: {stage}.md\n"
        f"reviewer_session_id: test-{stage}\n"
        f"review_version: {version}\n"
        f"---\n\n"
        f"## deletion_proposals\n\nnone\n\n"
        f"## verdict\n\n`{verdict}`\n\n"
        f"## conditions\n\n[]\n"
    )


def write_plan(trace: Path, version: int = 1) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "plan.md").write_text(
        f"---\ntask_id: test-task\nplan_version: {version}\n---\n\n"
        f"## recommended\n\nboring-default\n"
    )


def write_build_summary(trace: Path, scope_creep_count: int = 0) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    flags = (
        "\n".join(f"- scope creep item {i + 1}" for i in range(scope_creep_count))
        if scope_creep_count
        else "none"
    )
    (trace / "build-summary.md").write_text(
        f"---\ntask_id: test-task\n---\n\n## scope_creep_flags\n\n{flags}\n"
    )


def write_record(trace: Path, version: int = 1) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "record.md").write_text(
        f"---\ntask_id: test-task\ncompleted_at: 2026-04-15T10:00:00Z\n"
        f"task_level: L1\nrecord_version: {version}\n---\n\n"
        f"## skip_reason\n\nL0 change.\n"
    )


# ── Parser unit tests ─────────────────────────────────────────────────

class TestParsers:
    def test_frontmatter_string(self):
        fm = parse_frontmatter("---\nkey: value\n---\nbody")
        assert fm["key"] == "value"

    def test_frontmatter_int(self):
        fm = parse_frontmatter("---\nnum: 42\n---\n")
        assert fm["num"] == 42

    def test_frontmatter_bool_true(self):
        fm = parse_frontmatter("---\nflag: true\n---\n")
        assert fm["flag"] is True

    def test_frontmatter_bool_false(self):
        fm = parse_frontmatter("---\nforced_level: false\n---\n")
        assert fm["forced_level"] is False

    def test_frontmatter_empty_value(self):
        fm = parse_frontmatter('---\noverride_reason: ""\n---\n')
        assert fm["override_reason"] == ""

    def test_frontmatter_no_block(self):
        assert parse_frontmatter("no frontmatter here") == {}

    def test_section_found(self):
        text = "---\n---\n## first\ncontent here\n## second\nother"
        assert parse_section(text, "first") == "content here"

    def test_section_last(self):
        text = "## only\ncontent"
        assert parse_section(text, "only") == "content"

    def test_section_not_found(self):
        assert parse_section("## one\ncontent", "missing") is None

    def test_extract_verdict_backtick(self):
        text = "## verdict\n\n`approved`\n\n## next\n"
        assert extract_verdict(text) == "approved"

    def test_extract_verdict_with_conditions(self):
        text = "## verdict\n\n`approved-with-conditions`\n"
        assert extract_verdict(text) == "approved-with-conditions"

    def test_extract_verdict_rejected(self):
        text = "## verdict\n\n`rejected`\n"
        assert extract_verdict(text) == "rejected"

    def test_extract_verdict_template_residue(self):
        # Template placeholder — pick first token
        text = "## verdict\n\n`approved` | `approved-with-conditions` | `rejected`\n"
        assert extract_verdict(text) == "approved"

    def test_extract_verdict_missing_section(self):
        assert extract_verdict("no verdict here") is None


# ── Status stage inference ────────────────────────────────────────────

class TestStatusStage:
    def test_empty_trace_dir(self, tmp_path):
        task_dir = tmp_path / "t"
        task_dir.mkdir()
        s = load_task_status("t", tmp_path)
        assert s.current_stage == "Pre-Spec"
        assert s.pending_gate is not None
        assert not s.is_complete

    def test_spec_only(self, tmp_path):
        write_spec(tmp_path / "t")
        s = load_task_status("t", tmp_path)
        assert "Spec" in s.current_stage
        assert "Gate 1" in (s.pending_gate or "")

    def test_spec_with_rejected_review(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "rejected")
        s = load_task_status("t", tmp_path)
        assert "Spec" in s.current_stage
        assert "Gate 1" in (s.pending_gate or "")

    def test_spec_approved_waiting_for_plan(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        s = load_task_status("t", tmp_path)
        assert "Plan" in s.current_stage
        assert s.pending_gate is None

    def test_plan_waiting_for_review(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        s = load_task_status("t", tmp_path)
        assert "Plan" in s.current_stage
        assert "Gate 2" in (s.pending_gate or "")

    def test_plan_approved_waiting_for_build(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        write_review(tmp_path / "t", "plan", "approved")
        s = load_task_status("t", tmp_path)
        assert "Build" in s.current_stage
        assert s.pending_gate is None

    def test_build_with_scope_creep(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        write_review(tmp_path / "t", "plan", "approved")
        write_build_summary(tmp_path / "t", scope_creep_count=2)
        s = load_task_status("t", tmp_path)
        assert "scope creep" in s.current_stage.lower()
        assert "Gate 3" in (s.pending_gate or "")

    def test_build_clean_waiting_for_verify(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        write_review(tmp_path / "t", "plan", "approved")
        write_build_summary(tmp_path / "t", scope_creep_count=0)
        s = load_task_status("t", tmp_path)
        assert "Verify" in s.current_stage
        assert "Gate 4" in (s.pending_gate or "")

    def test_verify_approved_waiting_for_record(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        write_review(tmp_path / "t", "plan", "approved")
        write_build_summary(tmp_path / "t", scope_creep_count=0)
        write_review(tmp_path / "t", "build", "approved")
        s = load_task_status("t", tmp_path)
        assert "Record" in s.current_stage
        assert s.pending_gate is None

    def test_complete_task(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t")
        write_review(tmp_path / "t", "plan", "approved")
        write_build_summary(tmp_path / "t", scope_creep_count=0)
        write_review(tmp_path / "t", "build", "approved")
        write_record(tmp_path / "t")
        s = load_task_status("t", tmp_path)
        assert s.is_complete
        assert s.pending_gate is None

    def test_missing_trace_dir(self, tmp_path):
        s = load_task_status("nonexistent", tmp_path)
        assert "not found" in s.current_stage.lower()


# ── Rollback and bypass markers ───────────────────────────────────────

class TestMarkers:
    def test_rollback_detected_on_spec(self, tmp_path):
        write_spec(tmp_path / "t", version=2)
        s = load_task_status("t", tmp_path)
        assert any("spec.md" in m for m in s.rollback_markers)

    def test_no_rollback_when_version_1(self, tmp_path):
        write_spec(tmp_path / "t", version=1)
        s = load_task_status("t", tmp_path)
        assert s.rollback_markers == []

    def test_rollback_detected_on_plan(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        write_plan(tmp_path / "t", version=3)
        s = load_task_status("t", tmp_path)
        assert any("plan.md" in m for m in s.rollback_markers)

    def test_bypass_detected(self, tmp_path):
        write_spec(tmp_path / "t", forced=True, reason="L0 hotfix under time pressure")
        s = load_task_status("t", tmp_path)
        assert s.forced
        assert any("forced_level=true" in m for m in s.bypass_markers)
        assert "hotfix" in s.bypass_markers[0]

    def test_no_bypass_when_not_forced(self, tmp_path):
        write_spec(tmp_path / "t", forced=False)
        s = load_task_status("t", tmp_path)
        assert not s.forced
        assert s.bypass_markers == []


# ── Output formatting ─────────────────────────────────────────────────

class TestFormatting:
    def test_format_contains_task_id(self, tmp_path):
        write_spec(tmp_path / "my-task")
        s = load_task_status("my-task", tmp_path)
        out = format_status(s)
        assert "my-task" in out

    def test_format_shows_all_artifacts(self, tmp_path):
        write_spec(tmp_path / "t")
        s = load_task_status("t", tmp_path)
        out = format_status(s)
        for name in ("spec.md", "review-spec.md", "plan.md", "review-plan.md",
                     "build-summary.md", "review-build.md", "record.md"):
            assert name in out

    def test_format_shows_verdict(self, tmp_path):
        write_spec(tmp_path / "t")
        write_review(tmp_path / "t", "spec", "approved")
        s = load_task_status("t", tmp_path)
        out = format_status(s)
        assert "approved" in out

    def test_format_shows_rollback(self, tmp_path):
        write_spec(tmp_path / "t", version=2)
        s = load_task_status("t", tmp_path)
        out = format_status(s)
        assert "v2" in out
        assert "spec.md" in out

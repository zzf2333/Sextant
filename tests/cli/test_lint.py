"""Tests for sextant lint command."""
from __future__ import annotations
from pathlib import Path

import pytest

from cli.lint import lint_task, format_lint_report, Issue


# ── Fixture helpers ───────────────────────────────────────────────────

def write_spec(trace: Path, *, version: int = 1, forced: bool = False,
               reason: str = "", task_id: str = "t") -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "spec.md").write_text(
        f"---\ntask_id: {task_id}\nspec_version: {version}\n"
        f"forced_level: {str(forced).lower()}\n"
        f'override_reason: "{reason}"\n---\n\n## scope\n\ntest\n'
    )


def write_review(trace: Path, stage: str, verdict: str, version: int = 1,
                 deletion_proposals: str = "none") -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / f"review-{stage}.md").write_text(
        f"---\nstage: {stage}\nreviewed_artifact_ref: {stage}.md\n"
        f"reviewer_session_id: s-{stage}\nreview_version: {version}\n---\n\n"
        f"## deletion_proposals\n\n{deletion_proposals}\n\n"
        f"## verdict\n\n`{verdict}`\n\n"
        f"## conditions\n\n[]\n"
    )


def write_plan(trace: Path, version: int = 1, level: str = "L1") -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "plan.md").write_text(
        f"---\ntask_id: t\nspec_ref: spec.md\nplan_version: {version}\n"
        f"task_level: {level}\n---\n\n## candidates\n\n### A\n\n"
        f"## recommended\n\nA\n\n## rationale\n\nsimple\n\n"
        f"## engineering_footprint\n\n```yaml\nnew_files: []\n```\n"
    )


def write_build_summary(trace: Path, scope_creep: str = "none") -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / "build-summary.md").write_text(
        f"---\n---\n\n"
        f"## spec_ref\n\nspec.md\n\n"
        f"## plan_ref\n\nplan.md\n\n"
        f"## changes_summary\n\n- modified foo.py\n\n"
        f"## footprint_delta\n\nnone\n\n"
        f"## scope_creep_flags\n\n{scope_creep}\n\n"
        f"## hooks_passed\n\nnone\n"
    )


def write_record(trace: Path, version: int = 1, level: str = "L1",
                 has_skip_reason: bool = True) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    skip = "## skip_reason\n\nL0 change.\n" if has_skip_reason else ""
    (trace / "record.md").write_text(
        f"---\ntask_id: t\ncompleted_at: 2026-04-15T10:00:00Z\n"
        f"task_level: {level}\nrecord_version: {version}\n---\n\n{skip}"
    )


# ── Clean-pass tests ──────────────────────────────────────────────────

class TestCleanPass:
    def test_valid_spec_passes(self, tmp_path):
        write_spec(tmp_path / "t")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors
        assert code == 0

    def test_valid_review_passes(self, tmp_path):
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals="none")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_valid_review_with_proposals_passes(self, tmp_path):
        dp = "- spec.constraints[1]: redundant — already in SEXTANT.md"
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals=dp)
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_valid_plan_passes(self, tmp_path):
        write_plan(tmp_path / "t")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_valid_build_summary_passes(self, tmp_path):
        write_build_summary(tmp_path / "t")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_valid_record_passes(self, tmp_path):
        write_record(tmp_path / "t")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors


# ── spec.md checks ────────────────────────────────────────────────────

class TestSpecLint:
    def test_missing_task_id(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "spec.md").write_text(
            "---\nspec_version: 1\nforced_level: false\noverride_reason: \"\"\n---\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("task_id" in i.message for i in issues if i.level == "error")
        assert code == 1

    def test_forced_level_without_reason(self, tmp_path):
        write_spec(tmp_path / "t", forced=True, reason="")
        issues, code = lint_task("t", tmp_path)
        assert any("override_reason" in i.message for i in issues if i.level == "error")
        assert code == 1

    def test_forced_level_with_reason_passes(self, tmp_path):
        write_spec(tmp_path / "t", forced=True, reason="L0 hotfix under time pressure")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_invalid_spec_version(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "spec.md").write_text(
            "---\ntask_id: t\nspec_version: 0\nforced_level: false\noverride_reason: \"\"\n---\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("spec_version" in i.message for i in issues if i.level == "error")


# ── review deletion_proposals checks ─────────────────────────────────

class TestDeletionProposals:
    def test_missing_section_is_error(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "review-spec.md").write_text(
            "---\nstage: spec\nreviewed_artifact_ref: spec.md\n"
            "reviewer_session_id: s\nreview_version: 1\n---\n\n"
            "## verdict\n\n`approved`\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("deletion_proposals" in i.message and "missing" in i.message
                   for i in issues if i.level == "error")
        assert code == 1

    def test_placeholder_todo_is_error(self, tmp_path):
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals="- TODO")
        issues, code = lint_task("t", tmp_path)
        assert any("placeholder" in i.message for i in issues if i.level == "error")
        assert code == 1

    def test_placeholder_na_is_error(self, tmp_path):
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals="- n/a")
        issues, code = lint_task("t", tmp_path)
        assert any("placeholder" in i.message for i in issues if i.level == "error")

    def test_empty_content_not_none(self, tmp_path):
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals="")
        issues, code = lint_task("t", tmp_path)
        # Empty content (not "none") should be flagged
        errors = [i for i in issues if i.level == "error" and "deletion_proposals" in i.message]
        assert len(errors) > 0

    def test_valid_none_literal_passes(self, tmp_path):
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals="none")
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors

    def test_valid_bullet_proposals_pass(self, tmp_path):
        dp = "- plan.candidate_b: adds Redis for no reason — remove\n- spec.constraint_3: redundant"
        write_review(tmp_path / "t", "spec", "approved", deletion_proposals=dp)
        issues, code = lint_task("t", tmp_path)
        errors = [i for i in issues if i.level == "error"]
        assert errors == [], errors


# ── verdict checks ────────────────────────────────────────────────────

class TestVerdictLint:
    def test_invalid_verdict_is_error(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "review-spec.md").write_text(
            "---\nstage: spec\nreviewed_artifact_ref: spec.md\n"
            "reviewer_session_id: s\nreview_version: 1\n---\n\n"
            "## deletion_proposals\n\nnone\n\n"
            "## verdict\n\n`maybe`\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("verdict" in i.message and "valid" in i.message
                   for i in issues if i.level == "error")
        assert code == 1

    def test_template_residue_is_error(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "review-spec.md").write_text(
            "---\nstage: spec\nreviewed_artifact_ref: spec.md\n"
            "reviewer_session_id: s\nreview_version: 1\n---\n\n"
            "## deletion_proposals\n\nnone\n\n"
            "## verdict\n\n`approved` | `approved-with-conditions` | `rejected`\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("placeholder" in i.message.lower() or "template" in i.message.lower()
                   for i in issues if i.level == "error")
        assert code == 1

    def test_all_valid_verdicts_pass(self, tmp_path):
        for verdict in ("approved", "approved-with-conditions", "changes-requested", "rejected"):
            trace = tmp_path / f"t-{verdict}"
            write_review(trace, "spec", verdict, deletion_proposals="none")
            issues, code = lint_task(f"t-{verdict}", tmp_path)
            errors = [i for i in issues if i.level == "error"]
            assert errors == [], f"verdict '{verdict}' should pass but got errors: {errors}"


# ── build-summary checks ──────────────────────────────────────────────

class TestBuildSummaryLint:
    def test_missing_section_is_error(self, tmp_path):
        (tmp_path / "t").mkdir()
        # Missing hooks_passed section
        (tmp_path / "t" / "build-summary.md").write_text(
            "---\n---\n\n"
            "## spec_ref\n\nspec.md\n\n"
            "## plan_ref\n\nplan.md\n\n"
            "## changes_summary\n\n- foo\n\n"
            "## footprint_delta\n\nnone\n\n"
            "## scope_creep_flags\n\nnone\n"
            # hooks_passed intentionally missing
        )
        issues, code = lint_task("t", tmp_path)
        assert any("hooks_passed" in i.message for i in issues if i.level == "error")
        assert code == 1

    def test_scope_creep_with_items_is_warning(self, tmp_path):
        write_build_summary(tmp_path / "t", scope_creep="- added extra util\n- added tests")
        issues, code = lint_task("t", tmp_path)
        warnings = [i for i in issues if i.level == "warning" and "scope_creep" in i.message]
        assert warnings, "scope_creep_flags with items should produce a warning"
        assert code == 0  # warning only, not error


# ── record checks ─────────────────────────────────────────────────────

class TestRecordLint:
    def test_missing_both_sections_is_error(self, tmp_path):
        write_record(tmp_path / "t", has_skip_reason=False)
        issues, code = lint_task("t", tmp_path)
        assert any("knowledge_writebacks" in i.message or "skip_reason" in i.message
                   for i in issues if i.level == "error")
        assert code == 1

    def test_invalid_task_level(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "record.md").write_text(
            "---\ntask_id: t\ncompleted_at: 2026-04-15T10:00:00Z\n"
            "task_level: L3\nrecord_version: 1\n---\n\n## skip_reason\n\ntest\n"
        )
        issues, code = lint_task("t", tmp_path)
        assert any("task_level" in i.message for i in issues if i.level == "error")
        assert code == 1


# ── Trace directory checks ────────────────────────────────────────────

class TestTraceDirectory:
    def test_unexpected_file_is_warning(self, tmp_path):
        (tmp_path / "t").mkdir()
        (tmp_path / "t" / "notes.md").write_text("scratch notes")
        issues, code = lint_task("t", tmp_path)
        warnings = [i for i in issues if i.level == "warning" and "whitelist" in i.message]
        assert warnings
        assert code == 0  # warning only

    def test_missing_trace_dir_is_error(self, tmp_path):
        issues, code = lint_task("nonexistent", tmp_path)
        assert code == 1
        assert any("not found" in i.message for i in issues)


# ── Report formatting ─────────────────────────────────────────────────

class TestReportFormatting:
    def test_clean_report_shows_pass(self, tmp_path):
        write_spec(tmp_path / "t")
        issues, code = lint_task("t", tmp_path)
        report = format_lint_report("t", issues, code)
        assert "0 errors" in report or "passed" in report

    def test_error_report_shows_count(self, tmp_path):
        write_spec(tmp_path / "t", forced=True, reason="")
        issues, code = lint_task("t", tmp_path)
        report = format_lint_report("t", issues, code)
        assert "1 error" in report or "errors" in report

    def test_warning_only_exit_code_zero(self, tmp_path):
        write_build_summary(tmp_path / "t", scope_creep="- item1")
        issues, code = lint_task("t", tmp_path)
        assert code == 0

"""Tests for sextant metrics command."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cli.metrics import (
    ReviewSummary,
    collect_reviews,
    compute_metrics,
    format_metrics,
)


# ── Fixture builders ──────────────────────────────────────────────────

def make_review(trace: Path, stage: str, verdict: str = "approved",
                has_non_none: bool = False) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    dp = "- something to delete" if has_non_none else "none"
    (trace / f"review-{stage}.md").write_text(
        f"---\nstage: {stage}\nreviewed_artifact_ref: {stage}.md\n"
        f"reviewer_session_id: s\nreview_version: 1\n---\n\n"
        f"## deletion_proposals\n\n{dp}\n\n"
        f"## verdict\n\n`{verdict}`\n\n"
        f"## conditions\n\n[]\n"
    )


def make_record(trace: Path, completed_at: str = "2026-04-15T10:00:00Z") -> None:
    (trace / "record.md").write_text(
        f"---\ntask_id: {trace.name}\ncompleted_at: {completed_at}\n"
        f"task_level: L1\nrecord_version: 1\n---\n\n## skip_reason\n\ntest\n"
    )


def make_spec(trace: Path, level: str = "L1") -> None:
    (trace / "spec.md").write_text(
        f"---\ntask_id: {trace.name}\nspec_version: 1\n"
        f"task_level: {level}\nforced_level: false\noverride_reason: \"\"\n---\n"
    )


# ── collect_reviews ───────────────────────────────────────────────────

class TestCollectReviews:
    def test_empty_traces_dir(self, tmp_path):
        assert collect_reviews(tmp_path) == []

    def test_nonexistent_traces_dir(self, tmp_path):
        assert collect_reviews(tmp_path / "nonexistent") == []

    def test_collects_one_review(self, tmp_path):
        make_review(tmp_path / "t1", "spec", "approved")
        reviews = collect_reviews(tmp_path)
        assert len(reviews) == 1
        assert reviews[0].task_id == "t1"
        assert reviews[0].stage == "spec"
        assert reviews[0].verdict == "approved"

    def test_collects_multiple_reviews_per_task(self, tmp_path):
        make_review(tmp_path / "t1", "spec", "approved")
        make_review(tmp_path / "t1", "plan", "approved")
        make_review(tmp_path / "t1", "build", "approved")
        reviews = collect_reviews(tmp_path)
        assert len(reviews) == 3

    def test_collects_across_tasks(self, tmp_path):
        for i in range(3):
            make_review(tmp_path / f"task-{i}", "spec", "approved")
        reviews = collect_reviews(tmp_path)
        assert len(reviews) == 3

    def test_non_none_dp_detected(self, tmp_path):
        make_review(tmp_path / "t", "spec", "approved", has_non_none=True)
        reviews = collect_reviews(tmp_path)
        assert reviews[0].has_non_none_proposals is True

    def test_none_dp_detected(self, tmp_path):
        make_review(tmp_path / "t", "spec", "approved", has_non_none=False)
        reviews = collect_reviews(tmp_path)
        assert reviews[0].has_non_none_proposals is False

    def test_level_filter(self, tmp_path):
        t1 = tmp_path / "t1"
        t2 = tmp_path / "t2"
        make_review(t1, "spec", "approved")
        make_spec(t1, level="L1")
        make_review(t2, "spec", "approved")
        make_spec(t2, level="L2")
        reviews = collect_reviews(tmp_path, task_levels=["L1"])
        assert all(r.task_id == "t1" for r in reviews)


# ── compute_metrics ───────────────────────────────────────────────────

class TestComputeMetrics:
    def test_empty_reviews(self):
        report = compute_metrics([])
        assert report.total_reviews == 0
        assert report.non_empty_dp_ratio is None

    def test_all_none_dp(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t1", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.non_empty_dp_ratio == 0.0
        assert report.consecutive_none_tasks == 1.0

    def test_all_with_proposals(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=True,
                          completed_at=None),
            ReviewSummary("t2", "spec", "approved", has_non_none_proposals=True,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.non_empty_dp_ratio == 1.0
        assert report.consecutive_none_tasks == 0.0

    def test_rejection_ratio(self):
        reviews = [
            ReviewSummary("t1", "spec", "rejected", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t1", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t2", "spec", "changes-requested", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t2", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.reviewer_rejection_ratio == 0.5

    def test_consecutive_none_partial(self):
        # t1: all none, t2: one has proposals -> 0.5
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t1", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t2", "spec", "approved", has_non_none_proposals=True,
                          completed_at=None),
            ReviewSummary("t2", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.consecutive_none_tasks == 0.5

    def test_verdict_counts(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t2", "spec", "rejected", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t3", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.verdict_counts["approved"] == 2
        assert report.verdict_counts["rejected"] == 1

    def test_total_tasks_is_unique_ids(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t1", "plan", "approved", has_non_none_proposals=False,
                          completed_at=None),
            ReviewSummary("t2", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        assert report.total_tasks == 2
        assert report.total_reviews == 3


# ── Format output ─────────────────────────────────────────────────────

class TestFormatMetrics:
    def test_empty_shows_no_data_message(self):
        report = compute_metrics([])
        output = format_metrics(report)
        assert "No review data" in output

    def test_populated_shows_ratios(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=True,
                          completed_at=None),
            ReviewSummary("t2", "spec", "rejected", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        output = format_metrics(report)
        assert "deletion_proposals" in output
        assert "%" in output

    def test_output_contains_drift_warning(self):
        reviews = [
            ReviewSummary("t1", "spec", "approved", has_non_none_proposals=False,
                          completed_at=None),
        ]
        report = compute_metrics(reviews)
        output = format_metrics(report)
        assert "drift" in output.lower() or "signal" in output.lower()

    def test_filter_label_in_output(self):
        report = compute_metrics([], since_days=30, task_levels=["L2"])
        output = format_metrics(report)
        assert "30 days" in output
        assert "L2" in output

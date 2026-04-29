"""Tests for sextant tokens and sextant record-usage commands."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from cli.tokens import (
    STAGE_INPUT_RULES,
    STAGE_ORDER,
    STAGE_OUTPUT_ARTIFACTS,
    TokenSummary,
    TokenReport,
    estimate_tokens,
    collect_tokens,
    compute_tokens,
    format_tokens,
    read_usage_json,
    write_usage_json,
)


# ── Fixture builders ──────────────────────────────────────────────────

def make_artifact(trace: Path, filename: str, content: str = "x" * 400) -> None:
    trace.mkdir(parents=True, exist_ok=True)
    (trace / filename).write_text(content, encoding="utf-8")


def make_record(trace: Path, completed_at: str = "2026-04-15T10:00:00Z",
                level: str = "L1") -> None:
    (trace / "record.md").write_text(
        f"---\ntask_id: {trace.name}\ncompleted_at: {completed_at}\n"
        f"task_level: {level}\nrecord_version: 1\n---\n\n## skip_reason\n\ntest\n",
        encoding="utf-8",
    )


def make_spec(trace: Path, level: str = "L1") -> None:
    (trace / "spec.md").write_text(
        f"---\ntask_id: {trace.name}\nspec_version: 1\n"
        f"task_level: {level}\nforced_level: false\noverride_reason: \"\"\n---\n",
        encoding="utf-8",
    )


def make_full_trace(traces: Path, name: str = "task-1", level: str = "L1") -> Path:
    trace = traces / name
    trace.mkdir(parents=True, exist_ok=True)
    make_spec(trace, level=level)
    make_artifact(trace, "plan.md", "x" * 800)
    make_artifact(trace, "build-summary.md", "x" * 1200)
    make_artifact(trace, "review-spec.md", "x" * 200)
    make_artifact(trace, "review-plan.md", "x" * 200)
    make_artifact(trace, "review-build.md", "x" * 300)
    make_record(trace, level=level)
    return trace


# ── TestEstimateTokens ────────────────────────────────────────────────

class TestEstimateTokens:
    def test_1000_chars_gives_250(self, tmp_path):
        f = tmp_path / "f.md"
        f.write_text("a" * 1000, encoding="utf-8")
        assert estimate_tokens(f) == 250

    def test_missing_file_gives_zero(self, tmp_path):
        assert estimate_tokens(tmp_path / "nonexistent.md") == 0

    def test_empty_file_gives_zero(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        assert estimate_tokens(f) == 0

    def test_integer_division(self, tmp_path):
        f = tmp_path / "f.md"
        f.write_text("a" * 1001, encoding="utf-8")
        assert estimate_tokens(f) == 250  # 1001 // 4 == 250

    def test_400_chars_gives_100(self, tmp_path):
        f = tmp_path / "f.md"
        f.write_text("x" * 400, encoding="utf-8")
        assert estimate_tokens(f) == 100


# ── TestStageInputRules ───────────────────────────────────────────────

class TestStageInputRules:
    def test_all_seven_stages_present(self):
        assert set(STAGE_INPUT_RULES.keys()) == set(STAGE_ORDER)

    def test_each_stage_has_non_empty_list(self):
        for stage, rules in STAGE_INPUT_RULES.items():
            assert len(rules) > 0, f"Stage {stage!r} has empty input rules"

    def test_role_owning_stages_include_core_roles_path(self):
        role_stages = {"spec", "review-spec", "plan", "review-plan", "build", "review-build"}
        for stage in role_stages:
            bases = [base for base, _ in STAGE_INPUT_RULES[stage]]
            assert "core" in bases, f"Stage {stage!r} missing role prompt (core entry)"

    def test_record_has_no_role_prompt(self):
        bases = [base for base, _ in STAGE_INPUT_RULES["record"]]
        assert "core" not in bases

    def test_review_stages_include_upstream_artifact(self):
        review_artifact_map = {
            "review-spec": "spec.md",
            "review-plan": "plan.md",
            "review-build": "build-summary.md",
        }
        for stage, expected_artifact in review_artifact_map.items():
            trace_entries = [rel for base, rel in STAGE_INPUT_RULES[stage] if base == "trace"]
            assert expected_artifact in trace_entries, (
                f"Stage {stage!r} missing expected upstream artifact {expected_artifact!r}"
            )

    def test_all_seven_stages_have_output_artifact(self):
        assert set(STAGE_OUTPUT_ARTIFACTS.keys()) == set(STAGE_ORDER)


# ── TestUsageJson ─────────────────────────────────────────────────────

class TestReadUsageJson:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert read_usage_json(tmp_path) == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        (tmp_path / "usage.json").write_text("not json", encoding="utf-8")
        assert read_usage_json(tmp_path) == {}

    def test_valid_file_returns_parsed_data(self, tmp_path):
        data = {"task_id": "t1", "stages": {"spec": {"input_tokens": 100}}}
        (tmp_path / "usage.json").write_text(json.dumps(data), encoding="utf-8")
        result = read_usage_json(tmp_path)
        assert result["task_id"] == "t1"
        assert result["stages"]["spec"]["input_tokens"] == 100


class TestWriteUsageJson:
    def test_creates_file_if_absent(self, tmp_path):
        write_usage_json(tmp_path, stage="spec", input_tokens=100, output_tokens=50)
        assert (tmp_path / "usage.json").exists()

    def test_written_data_is_valid_json(self, tmp_path):
        write_usage_json(tmp_path, stage="spec", input_tokens=100, output_tokens=50)
        data = json.loads((tmp_path / "usage.json").read_text())
        assert "stages" in data
        assert "spec" in data["stages"]

    def test_basic_fields_are_stored(self, tmp_path):
        write_usage_json(
            tmp_path, stage="spec",
            input_tokens=3200, output_tokens=840,
            cache_read_tokens=1200, cache_creation_tokens=400,
        )
        data = json.loads((tmp_path / "usage.json").read_text())
        s = data["stages"]["spec"]
        assert s["input_tokens"] == 3200
        assert s["output_tokens"] == 840
        assert s["cache_read_tokens"] == 1200
        assert s["cache_creation_tokens"] == 400
        assert s["total_tokens"] == 4040
        assert s["source"] == "recorded"

    def test_duration_computed_from_timestamps(self, tmp_path):
        write_usage_json(
            tmp_path, stage="spec",
            input_tokens=100, output_tokens=50,
            started_at="2026-04-20T10:00:00Z",
            completed_at="2026-04-20T10:08:30Z",
        )
        data = json.loads((tmp_path / "usage.json").read_text())
        assert data["stages"]["spec"]["duration_seconds"] == 510

    def test_explicit_duration_takes_precedence_over_timestamps(self, tmp_path):
        write_usage_json(
            tmp_path, stage="spec",
            input_tokens=100, output_tokens=50,
            started_at="2026-04-20T10:00:00Z",
            completed_at="2026-04-20T10:08:30Z",
            duration_seconds=999,
        )
        data = json.loads((tmp_path / "usage.json").read_text())
        assert data["stages"]["spec"]["duration_seconds"] == 999

    def test_model_stored_when_provided(self, tmp_path):
        write_usage_json(
            tmp_path, stage="spec",
            input_tokens=100, output_tokens=50,
            model="claude-sonnet-4-6",
        )
        data = json.loads((tmp_path / "usage.json").read_text())
        assert data["stages"]["spec"]["model"] == "claude-sonnet-4-6"

    def test_second_write_merges_stages(self, tmp_path):
        write_usage_json(tmp_path, stage="spec", input_tokens=100, output_tokens=50)
        write_usage_json(tmp_path, stage="plan", input_tokens=200, output_tokens=80)
        data = json.loads((tmp_path / "usage.json").read_text())
        assert "spec" in data["stages"]
        assert "plan" in data["stages"]

    def test_overwrite_existing_stage(self, tmp_path):
        write_usage_json(tmp_path, stage="spec", input_tokens=100, output_tokens=50)
        write_usage_json(tmp_path, stage="spec", input_tokens=999, output_tokens=111)
        data = json.loads((tmp_path / "usage.json").read_text())
        assert data["stages"]["spec"]["input_tokens"] == 999

    def test_task_id_set_from_dir_name(self, tmp_path):
        task_dir = tmp_path / "2026-04-20-my-task"
        task_dir.mkdir()
        write_usage_json(task_dir, stage="spec", input_tokens=100, output_tokens=50)
        data = json.loads((task_dir / "usage.json").read_text())
        assert data["task_id"] == "2026-04-20-my-task"

    def test_invalid_timestamps_skip_duration_computation(self, tmp_path):
        write_usage_json(
            tmp_path, stage="spec",
            input_tokens=100, output_tokens=50,
            started_at="not-a-date",
            completed_at="also-not-a-date",
        )
        data = json.loads((tmp_path / "usage.json").read_text())
        assert "duration_seconds" not in data["stages"]["spec"]


# ── TestCollectTokens ─────────────────────────────────────────────────

class TestCollectTokens:
    def test_empty_traces_dir(self, tmp_path):
        assert collect_tokens(tmp_path) == []

    def test_nonexistent_traces_dir(self, tmp_path):
        assert collect_tokens(tmp_path / "nonexistent") == []

    def test_missing_artifacts_produce_zero_output_tokens(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-empty"
        trace.mkdir(parents=True)
        summaries = collect_tokens(traces)
        assert len(summaries) == len(STAGE_ORDER)
        for s in summaries:
            assert s.output_tokens == 0
            assert s.artifact_exists is False

    def test_present_artifact_produces_nonzero_output_tokens(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-1"
        trace.mkdir(parents=True)
        (trace / "spec.md").write_text("x" * 400, encoding="utf-8")
        summaries = collect_tokens(traces)
        spec_summary = next(s for s in summaries if s.stage == "spec")
        assert spec_summary.output_tokens == 100
        assert spec_summary.artifact_exists is True

    def test_returns_all_stages_per_task(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        make_full_trace(traces, "task-1")
        summaries = collect_tokens(traces)
        stages = [s.stage for s in summaries if s.task_id == "task-1"]
        assert set(stages) == set(STAGE_ORDER)

    def test_multiple_tasks(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        make_full_trace(traces, "task-1")
        make_full_trace(traces, "task-2")
        summaries = collect_tokens(traces)
        task_ids = {s.task_id for s in summaries}
        assert task_ids == {"task-1", "task-2"}

    def test_task_level_filter_excludes_non_matching(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        make_full_trace(traces, "task-l1", level="L1")
        make_full_trace(traces, "task-l2", level="L2")
        summaries = collect_tokens(traces, task_levels=["L1"])
        task_ids = {s.task_id for s in summaries}
        assert task_ids == {"task-l1"}

    def test_since_filter_excludes_old_tasks(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        make_full_trace(traces, "recent")
        (traces / "recent" / "record.md").write_text(
            "---\ntask_id: recent\ncompleted_at: 2020-01-01T00:00:00Z\n"
            "task_level: L1\nrecord_version: 1\n---\n\n## skip_reason\n\ntest\n",
            encoding="utf-8",
        )
        summaries = collect_tokens(traces, since_days=1)
        assert summaries == []

    def test_since_filter_excludes_incomplete_tasks(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "incomplete"
        trace.mkdir(parents=True)
        make_spec(trace)
        summaries = collect_tokens(traces, since_days=30)
        assert summaries == []

    def test_incomplete_tasks_included_without_since_filter(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "incomplete"
        trace.mkdir(parents=True)
        make_spec(trace)
        summaries = collect_tokens(traces)
        assert len(summaries) == len(STAGE_ORDER)

    def test_hidden_dirs_ignored(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        hidden = traces / ".index"
        hidden.mkdir(parents=True)
        summaries = collect_tokens(traces)
        assert summaries == []

    def test_recorded_stage_uses_usage_json_not_estimation(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-rec"
        trace.mkdir(parents=True)
        # Write a tiny artifact — estimation would give a small number
        (trace / "spec.md").write_text("x" * 40, encoding="utf-8")
        # Write usage.json with large explicit values
        write_usage_json(trace, stage="spec", input_tokens=9999, output_tokens=8888)
        summaries = collect_tokens(traces)
        spec_summary = next(s for s in summaries if s.stage == "spec")
        assert spec_summary.input_tokens == 9999
        assert spec_summary.output_tokens == 8888
        assert spec_summary.source == "recorded"

    def test_missing_usage_json_falls_back_to_estimation(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-est"
        trace.mkdir(parents=True)
        (trace / "spec.md").write_text("x" * 400, encoding="utf-8")
        # No usage.json
        summaries = collect_tokens(traces)
        spec_summary = next(s for s in summaries if s.stage == "spec")
        assert spec_summary.source == "estimated"
        assert spec_summary.output_tokens == 100  # 400 chars // 4

    def test_partial_usage_json_recorded_stages_preferred(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-partial"
        trace.mkdir(parents=True)
        # Record only spec stage
        write_usage_json(trace, stage="spec", input_tokens=5000, output_tokens=1000)
        summaries = collect_tokens(traces)
        spec_s = next(s for s in summaries if s.stage == "spec")
        plan_s = next(s for s in summaries if s.stage == "plan")
        assert spec_s.source == "recorded"
        assert plan_s.source == "estimated"

    def test_recorded_stage_carries_duration_and_model(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-dur"
        trace.mkdir(parents=True)
        write_usage_json(
            trace, stage="spec",
            input_tokens=100, output_tokens=50,
            started_at="2026-04-20T10:00:00Z",
            completed_at="2026-04-20T10:05:00Z",
            model="claude-sonnet-4-6",
        )
        summaries = collect_tokens(traces)
        spec_s = next(s for s in summaries if s.stage == "spec")
        assert spec_s.duration_seconds == 300
        assert spec_s.model == "claude-sonnet-4-6"

    def test_estimated_stage_has_no_duration(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-notime"
        trace.mkdir(parents=True)
        summaries = collect_tokens(traces)
        for s in summaries:
            assert s.duration_seconds is None

    def test_cache_tokens_from_usage_json(self, tmp_path):
        traces = tmp_path / ".sextant" / "traces"
        trace = traces / "task-cache"
        trace.mkdir(parents=True)
        write_usage_json(
            trace, stage="spec",
            input_tokens=3200, output_tokens=840,
            cache_read_tokens=1200, cache_creation_tokens=400,
        )
        summaries = collect_tokens(traces)
        spec_s = next(s for s in summaries if s.stage == "spec")
        assert spec_s.cache_read_tokens == 1200
        assert spec_s.cache_creation_tokens == 400


# ── TestComputeTokens ─────────────────────────────────────────────────

class TestComputeTokens:
    def test_empty_summaries(self):
        report = compute_tokens([])
        assert report.total_tasks == 0
        assert report.total_tokens == 0
        assert report.stage_breakdown == {}
        assert report.tasks == []

    def test_total_tokens_sums_input_and_output(self):
        summaries = [
            TokenSummary("t1", "spec", input_tokens=100, output_tokens=50, artifact_exists=True),
            TokenSummary("t1", "plan", input_tokens=200, output_tokens=80, artifact_exists=True),
        ]
        report = compute_tokens(summaries)
        assert report.total_tokens == 430

    def test_total_tasks_counts_unique_ids(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True),
            TokenSummary("t1", "plan", 200, 80, True),
            TokenSummary("t2", "spec", 150, 60, True),
        ]
        report = compute_tokens(summaries)
        assert report.total_tasks == 2

    def test_stage_breakdown_has_all_seven_stages(self):
        summaries = [
            TokenSummary("t1", stage, 100, 50, True) for stage in STAGE_ORDER
        ]
        report = compute_tokens(summaries)
        assert set(report.stage_breakdown.keys()) == set(STAGE_ORDER)

    def test_stage_breakdown_averages(self):
        summaries = [
            TokenSummary("t1", "spec", input_tokens=400, output_tokens=200, artifact_exists=True),
            TokenSummary("t2", "spec", input_tokens=600, output_tokens=400, artifact_exists=True),
        ]
        report = compute_tokens(summaries)
        bd = report.stage_breakdown["spec"]
        assert bd["avg_input_tokens"] == 500
        assert bd["avg_output_tokens"] == 300
        assert bd["avg_total_tokens"] == 800
        assert bd["task_count"] == 2

    def test_task_breakdown_includes_all_stages(self):
        summaries = [
            TokenSummary("t1", stage, 100, 50, True) for stage in STAGE_ORDER
        ]
        report = compute_tokens(summaries)
        assert len(report.tasks) == 1
        task = report.tasks[0]
        assert task["task_id"] == "t1"
        assert set(task["stages"].keys()) == set(STAGE_ORDER)

    def test_missing_stage_in_task_fills_zero(self):
        summaries = [
            TokenSummary("t1", "spec", input_tokens=100, output_tokens=50, artifact_exists=True),
        ]
        report = compute_tokens(summaries)
        task = report.tasks[0]
        plan_stage = task["stages"]["plan"]
        assert plan_stage["input"] == 0
        assert plan_stage["output"] == 0
        assert plan_stage["exists"] is False

    def test_kwargs_passed_to_report(self):
        report = compute_tokens([], since_days=7, task_levels=["L1"])
        assert report.since_days == 7
        assert report.task_levels == ["L1"]

    def test_recorded_tasks_count(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, source="recorded"),
            TokenSummary("t2", "spec", 100, 50, True, source="estimated"),
        ]
        report = compute_tokens(summaries)
        assert report.recorded_tasks == 1
        assert report.total_tasks == 2

    def test_timed_tasks_count(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, duration_seconds=120),
            TokenSummary("t2", "spec", 100, 50, True, duration_seconds=None),
        ]
        report = compute_tokens(summaries)
        assert report.timed_tasks == 1

    def test_total_duration_sums_all_timed_stages(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, duration_seconds=300),
            TokenSummary("t1", "plan", 200, 80, True, duration_seconds=600),
            TokenSummary("t2", "spec", 100, 50, True, duration_seconds=None),
        ]
        report = compute_tokens(summaries)
        assert report.total_duration_seconds == 900

    def test_total_duration_none_when_no_timing(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, duration_seconds=None)]
        report = compute_tokens(summaries)
        assert report.total_duration_seconds is None

    def test_stage_breakdown_avg_duration(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, duration_seconds=200),
            TokenSummary("t2", "spec", 100, 50, True, duration_seconds=400),
        ]
        report = compute_tokens(summaries)
        bd = report.stage_breakdown["spec"]
        assert bd["avg_duration_seconds"] == 300
        assert bd["timed_task_count"] == 2

    def test_stage_breakdown_avg_duration_none_when_no_timing(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, duration_seconds=None)]
        report = compute_tokens(summaries)
        bd = report.stage_breakdown["spec"]
        assert bd["avg_duration_seconds"] is None

    def test_cache_tokens_in_stage_breakdown(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True,
                         cache_read_tokens=200, cache_creation_tokens=100),
        ]
        report = compute_tokens(summaries)
        bd = report.stage_breakdown["spec"]
        assert bd["total_cache_read_tokens"] == 200
        assert bd["total_cache_creation_tokens"] == 100

    def test_per_task_duration_sum(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, duration_seconds=300),
            TokenSummary("t1", "plan", 200, 80, True, duration_seconds=600),
        ]
        report = compute_tokens(summaries)
        assert report.tasks[0]["total_duration_seconds"] == 900

    def test_per_task_duration_none_when_no_timing(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, duration_seconds=None)]
        report = compute_tokens(summaries)
        assert report.tasks[0]["total_duration_seconds"] is None


# ── TestFormatTokens ──────────────────────────────────────────────────

class TestFormatTokens:
    def test_empty_shows_no_data_message(self):
        report = compute_tokens([])
        output = format_tokens(report)
        assert "No task data" in output

    def test_aggregate_shows_summary_headers(self):
        summaries = [TokenSummary("t1", s, 100, 50, True) for s in STAGE_ORDER]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "Avg Tokens" in output
        assert "Avg Time" in output

    def test_aggregate_shows_all_stage_names(self):
        summaries = [TokenSummary("t1", s, 100, 50, True) for s in STAGE_ORDER]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        for stage in STAGE_ORDER:
            assert stage in output

    def test_aggregate_shows_total_tokens(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True)]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "150" in output  # 100 + 50

    def test_aggregate_shows_total_duration_when_timed(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, duration_seconds=300)]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "5m" in output

    def test_aggregate_shows_dash_for_no_duration(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, duration_seconds=None)]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "—" in output

    def test_filter_labels_in_output(self):
        report = compute_tokens([], since_days=30, task_levels=["L2"])
        output = format_tokens(report)
        assert "30 days" in output
        assert "L2" in output

    def test_detail_mode_shows_all_columns(self):
        summaries = [
            TokenSummary("task-1", "spec", input_tokens=500, output_tokens=200,
                         artifact_exists=True, cache_read_tokens=100,
                         duration_seconds=180, source="recorded"),
        ]
        report = compute_tokens(summaries)
        output = format_tokens(report, detail_task_id="task-1")
        assert "Input" in output
        assert "Output" in output
        assert "Total" in output
        assert "Time" in output
        assert "Source" in output
        assert "task-1" in output

    def test_detail_mode_unknown_task_returns_message(self):
        report = compute_tokens([])
        output = format_tokens(report, detail_task_id="nonexistent")
        assert "not found" in output.lower()

    def test_detail_mode_shows_present_missing_status(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, artifact_exists=True),
            TokenSummary("t1", "plan", 200, 0, artifact_exists=False),
        ]
        report = compute_tokens(summaries)
        output = format_tokens(report, detail_task_id="t1")
        assert "present" in output
        assert "missing" in output

    def test_detail_mode_shows_recorded_source(self):
        summaries = [
            TokenSummary("t1", "spec", 100, 50, True, source="recorded"),
        ]
        report = compute_tokens(summaries)
        output = format_tokens(report, detail_task_id="t1")
        assert "recorded" in output

    def test_json_output_is_valid_and_has_required_keys(self):
        import json as json_module
        from dataclasses import asdict
        summaries = [TokenSummary("t1", s, 100, 50, True) for s in STAGE_ORDER]
        report = compute_tokens(summaries)
        data = json_module.loads(json_module.dumps(asdict(report), default=str))
        assert "total_tasks" in data
        assert "total_tokens" in data
        assert "stage_breakdown" in data
        assert "tasks" in data
        assert "recorded_tasks" in data
        assert "timed_tasks" in data
        assert "total_duration_seconds" in data

    def test_json_stage_breakdown_has_all_seven_stages(self):
        import json as json_module
        from dataclasses import asdict
        summaries = [TokenSummary("t1", s, 100, 50, True) for s in STAGE_ORDER]
        report = compute_tokens(summaries)
        data = json_module.loads(json_module.dumps(asdict(report), default=str))
        assert set(data["stage_breakdown"].keys()) == set(STAGE_ORDER)

    def test_source_label_recorded_when_all_recorded(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, source="recorded")]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "recorded" in output

    def test_source_label_estimated_when_all_estimated(self):
        summaries = [TokenSummary("t1", "spec", 100, 50, True, source="estimated")]
        report = compute_tokens(summaries)
        output = format_tokens(report)
        assert "estimated" in output


# ── TestFmtDuration ───────────────────────────────────────────────────

from cli.tokens import _fmt_duration


class TestFmtDuration:
    def test_none_returns_dash(self):
        assert _fmt_duration(None) == "—"

    def test_zero_seconds(self):
        assert _fmt_duration(0) == "0s"

    def test_seconds_only(self):
        assert _fmt_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        assert _fmt_duration(310) == "5m 10s"

    def test_hours_minutes_seconds(self):
        assert _fmt_duration(3661) == "1h 01m 01s"

    def test_negative_treated_as_zero(self):
        assert _fmt_duration(-5) == "0s"

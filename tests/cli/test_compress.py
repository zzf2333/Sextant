"""Tests for cli.compress — context compression."""
from __future__ import annotations
import json
import gzip
import tempfile
from pathlib import Path

from cli.compress import (
    TraceSummary,
    compress_trace,
    find_compressible_traces,
    format_compression_report,
    _format_bytes,
)


class TestTraceSummary:
    def test_defaults(self):
        s = TraceSummary(task_id="task-1")
        assert s.task_id == "task-1"
        assert s.spec_summary == ""
        assert s.plan_summary == ""
        assert s.review_verdicts == {}
        assert s.scope_creep_count == 0
        assert s.original_file_count == 0

    def test_with_data(self):
        s = TraceSummary(
            task_id="t1",
            spec_summary="Build feature X",
            review_verdicts={"spec": "approved", "plan": "approved"},
            deletion_proposals=["Remove dead code"],
            scope_creep_count=2,
            original_file_count=7,
            original_size_bytes=4096,
        )
        assert s.spec_summary == "Build feature X"
        assert s.review_verdicts["spec"] == "approved"
        assert len(s.deletion_proposals) == 1


class TestCompressTrace:
    def test_compress_empty_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = Path(tmp) / "empty-task"
            trace_dir.mkdir()
            output_dir = Path(tmp) / "compressed"

            summary = compress_trace(trace_dir, output_dir, dry_run=True)
            assert summary is not None
            assert summary.task_id == "empty-task"
            assert summary.original_file_count == 0

    def test_compress_with_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = Path(tmp) / "task-with-spec"
            trace_dir.mkdir()
            (trace_dir / "spec.md").write_text("""---
task_id: "spec-task"
request_summary: "Add login feature"
spec_version: 1
---

## scope

**In scope:**
- Login page with email/password

**Out of scope:**
- Social login

## constraints

- Must support OAuth2
""")

            output_dir = Path(tmp) / "compressed"
            summary = compress_trace(trace_dir, output_dir, dry_run=True)
            assert summary is not None
            assert "Login page" in summary.spec_summary

    def test_compress_with_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = Path(tmp) / "reviewed-task"
            trace_dir.mkdir()
            (trace_dir / "review-spec.md").write_text("""---
stage: "spec"
reviewed_artifact_ref: "reviewed-task"
review_version: 1
---

## verdict

`approved`

## deletion_proposals

- Remove unused helper
""")

            output_dir = Path(tmp) / "compressed"
            summary = compress_trace(trace_dir, output_dir, dry_run=True)
            assert summary is not None
            assert summary.review_verdicts.get("spec") == "approved"

    def test_compress_writes_gzip(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace_dir = Path(tmp) / "task-x"
            trace_dir.mkdir()
            (trace_dir / "spec.md").write_text("""---
task_id: "task-x"
request_summary: "Test"
spec_version: 1
---

## scope

**In scope:**
- Something
""")

            output_dir = Path(tmp) / "compressed"
            summary = compress_trace(trace_dir, output_dir, dry_run=False)
            assert summary is not None

            gz_path = output_dir / "task-x.summary.json.gz"
            assert gz_path.exists()

            # Verify content
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                data = json.loads(f.read())
                assert data["task_id"] == "task-x"


class TestFindCompressibleTraces:
    def test_no_traces(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_dir = Path(tmp) / "traces"
            traces_dir.mkdir()
            result = find_compressible_traces(traces_dir, all_completed=True)
            assert result == []

    def test_find_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_dir = Path(tmp) / "traces"
            traces_dir.mkdir()
            task_dir = traces_dir / "completed-task"
            task_dir.mkdir()
            (task_dir / "record.md").write_text("""---
task_id: "completed-task"
completed_at: "2026-01-01T00:00:00Z"
record_version: 1
---

## knowledge_writebacks

none
""")

            result = find_compressible_traces(traces_dir, all_completed=True)
            assert len(result) == 1
            assert result[0].name == "completed-task"

    def test_find_by_task_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_dir = Path(tmp) / "traces"
            traces_dir.mkdir()
            (traces_dir / "specific-task").mkdir()

            result = find_compressible_traces(traces_dir, task_id="specific-task")
            assert len(result) == 1

    def test_find_by_task_id_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            traces_dir = Path(tmp) / "traces"
            traces_dir.mkdir()

            result = find_compressible_traces(traces_dir, task_id="nope")
            assert result == []


class TestFormatBytes:
    def test_zero(self):
        assert "0 B" in _format_bytes(0)

    def test_bytes(self):
        assert "500 B" == _format_bytes(500)

    def test_kilobytes(self):
        assert "1 KB" in _format_bytes(1024)
        assert "0 B" in _format_bytes(0)

    def test_megabytes(self):
        assert "1.0 MB" in _format_bytes(1024 * 1024)
        assert "2.5 MB" in _format_bytes(int(2.5 * 1024 * 1024))


class TestFormatCompressionReport:
    def test_empty(self):
        output = format_compression_report([], 0, dry_run=True)
        assert "DRY-RUN" in output
        assert "0" in output

    def test_with_summaries(self):
        summaries = [
            TraceSummary(
                task_id="task-a",
                review_verdicts={"spec": "approved"},
                original_size_bytes=2048,
            ),
            TraceSummary(
                task_id="task-b",
                review_verdicts={"spec": "approved", "plan": "changes-requested"},
                original_size_bytes=4096,
            ),
        ]
        output = format_compression_report(summaries, 6144, dry_run=False)
        assert "COMPRESSED" in output
        assert "task-a" in output
        assert "task-b" in output
        assert "2" in output  # trace count

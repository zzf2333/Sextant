"""Tests for cli.reviewer_agent — automated review gate."""
from __future__ import annotations
import tempfile
from pathlib import Path

from cli.reviewer_agent import (
    ReviewPacket,
    ReviewResult,
    build_review_packet,
    build_review_prompt,
    format_review_result,
    _parse_review_output,
    _empty_review_template,
)
from cli.contract import TaskContract


class TestReviewPacket:
    def test_create(self):
        packet = ReviewPacket(task_id="task-1", stage="build")
        assert packet.task_id == "task-1"
        assert packet.stage == "build"
        assert packet.facts == []

    def test_with_facts(self):
        packet = ReviewPacket(
            task_id="t1", stage="spec",
            facts=["Objective: build X", "Type: implementation"],
        )
        assert len(packet.facts) == 2

    def test_with_artifacts(self):
        packet = ReviewPacket(
            task_id="t1", stage="build",
            artifacts={"diff": "+changed line"},
        )
        assert "diff" in packet.artifacts
        assert packet.artifacts["diff"] == "+changed line"


class TestBuildReviewPacket:
    def test_minimal_packet(self):
        contract = TaskContract(
            task_id="task-min",
            objective="Build minimal feature",
            allowed_paths=["src/**"],
            acceptance=["make test"],
        )
        packet = build_review_packet(
            task_id="task-min",
            stage="build",
            contract=contract,
        )
        assert "task-min" in packet.facts[0]
        assert len(packet.facts) > 3  # task_id, stage, objective at minimum

    def test_packet_with_constraints(self):
        contract = TaskContract(
            task_id="constrained",
            objective="Constrained build",
            allowed_paths=["src/a/**"],
            forbidden_paths=["src/b/**"],
            constraints=["No new deps", "Keep < 100 lines"],
            acceptance=["npm test"],
            review_focus=["security", "perf"],
        )
        packet = build_review_packet(
            task_id="constrained",
            stage="build",
            contract=contract,
        )
        facts_text = " ".join(packet.facts)
        assert "No new deps" in facts_text
        assert "src/b/**" in facts_text
        assert "security" in facts_text

    def test_rubric_paths_exist(self):
        contract = TaskContract(
            task_id="with-rubric",
            objective="Test rubric",
            allowed_paths=["src/**"],
            acceptance=["make test"],
        )
        packet = build_review_packet(
            task_id="with-rubric",
            stage="spec",
            contract=contract,
        )
        assert len(packet.rubric_paths) >= 1  # at least reviewer.md


class TestBuildReviewPrompt:
    def test_prompt_contains_role(self):
        contract = TaskContract(
            task_id="prompt-test",
            objective="Test prompt",
            allowed_paths=["src/**"],
            acceptance=["make test"],
        )
        packet = build_review_packet(
            task_id="prompt-test",
            stage="build",
            contract=contract,
        )
        prompt = build_review_prompt(packet)
        assert "reviewer" in prompt.lower()
        assert "prompt-test" in prompt
        assert "Clean Context Packet" in prompt
        assert "deletion_proposals" in prompt.lower()

    def test_prompt_contains_reminders(self):
        contract = TaskContract(
            task_id="reminder-test",
            objective="Test reminders",
            allowed_paths=["src/**"],
            acceptance=["make test"],
        )
        packet = build_review_packet(
            task_id="reminder-test",
            stage="plan",
            contract=contract,
        )
        prompt = build_review_prompt(packet)
        assert "MANDATORY" in prompt
        assert "approved" in prompt.lower()
        assert "rejected" in prompt.lower()


class TestParseReviewOutput:
    def test_parse_approved(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Review

## Metadata
```yaml
stage: "build"
reviewed_artifact_ref: "task-1"
reviewer_session_id: "session-123"
review_version: 1
```

## context_boundary
```yaml
packet_type: clean_context_packet
contamination_detected: false
contamination_notes: ""
missing_facts: ""
```

## deletion_proposals
none

## verdict
`approved`

## conditions
[]
""")
            f.flush()
            result = ReviewResult(task_id="task-1")
            _parse_review_output(Path(f.name), result)
            assert result.verdict == "approved"
            assert result.deletion_proposals == []
            assert result.conditions == []
            assert result.context_boundary_clean

    def test_parse_with_conditions(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Review

## context_boundary
```yaml
packet_type: clean_context_packet
contamination_detected: false
contamination_notes: ""
missing_facts: ""
```

## deletion_proposals
- Remove unused function X
- Delete dead code in module Y

## verdict
`approved-with-conditions`

## conditions
- Fix the null check in line 42
- Add error handling
""")
            f.flush()
            result = ReviewResult(task_id="task-2")
            _parse_review_output(Path(f.name), result)
            assert result.verdict == "approved-with-conditions"
            assert len(result.deletion_proposals) == 2
            assert "Remove unused function X" in result.deletion_proposals
            assert len(result.conditions) == 2

    def test_parse_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Review

## context_boundary
```yaml
packet_type: clean_context_packet
contamination_detected: true
contamination_notes: "author reasoning included"
missing_facts: "module history"
```

## deletion_proposals
none

## verdict
`rejected`

## conditions
- Complete redesign required
""")
            f.flush()
            result = ReviewResult(task_id="task-3")
            _parse_review_output(Path(f.name), result)
            assert result.verdict == "rejected"
            assert not result.context_boundary_clean
            assert "author reasoning" in result.contamination_notes

    def test_parse_changes_requested(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Review

## context_boundary
```yaml
packet_type: clean_context_packet
contamination_detected: false
contamination_notes: ""
missing_facts: ""
```

## deletion_proposals
none

## verdict
`changes-requested`

## conditions
- Add unit tests for edge cases
- Refactor the parser
""")
            f.flush()
            result = ReviewResult(task_id="task-4")
            _parse_review_output(Path(f.name), result)
            assert result.verdict == "changes-requested"


class TestEmptyReviewTemplate:
    def test_contains_sections(self):
        tmpl = _empty_review_template("task-x", "build")
        assert "task-x" in tmpl
        assert "build" in tmpl
        assert "context_boundary" in tmpl
        assert "deletion_proposals" in tmpl
        assert "verdict" in tmpl
        assert "conditions" in tmpl

    def test_verdict_placeholder(self):
        tmpl = _empty_review_template("t1", "spec")
        assert "approved" in tmpl
        assert "rejected" in tmpl


class TestFormatReviewResult:
    def test_approved(self):
        rr = ReviewResult(task_id="t1", verdict="approved")
        output = format_review_result(rr)
        assert "APPROVED" in output

    def test_rejected(self):
        rr = ReviewResult(task_id="t1", verdict="rejected")
        output = format_review_result(rr)
        assert "REJECTED" in output

    def test_with_proposals(self):
        rr = ReviewResult(
            task_id="t1",
            verdict="approved-with-conditions",
            deletion_proposals=["Remove X", "Delete Y"],
            conditions=["Fix bug"],
        )
        output = format_review_result(rr)
        assert "Remove X" in output
        assert "Delete Y" in output
        assert "Fix bug" in output

    def test_contamination(self):
        rr = ReviewResult(
            task_id="t1",
            verdict="approved",
            context_boundary_clean=False,
            contamination_notes="author reasoning leaked",
        )
        output = format_review_result(rr)
        assert "CONTAMINATED" in output

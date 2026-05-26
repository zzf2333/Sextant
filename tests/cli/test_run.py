"""Tests for cli.run — DAG executor and parallel execution."""
from __future__ import annotations
import tempfile
import json
from pathlib import Path
from cli.run import (
    TaskResult,
    DAGResult,
    DAGExecutor,
    _format_dag_summary,
    _format_results_summary,
)
from cli.validator import ValidationResult
from cli.scheduler import TaskDAG, TaskNode, load_dag, parse_dag_yaml


SAMPLE_DAG_YAML = """id: feature-agent-runtime-v2

tasks:
  - id: runtime-contract
    type: foundation
    depends_on: []
    parallelizable: false
    independent_verification: true

  - id: runtime-worker
    type: implementation
    depends_on:
      - runtime-contract
    parallelizable: true
    independent_verification: true

  - id: ui-panel
    type: implementation
    depends_on:
      - runtime-contract
    parallelizable: true
    independent_verification: true

  - id: integration-e2e
    type: integration
    depends_on:
      - runtime-worker
      - ui-panel
    parallelizable: false
    independent_verification: false
"""


class TestTaskResult:
    """TaskResult tests."""

    def test_success_result(self):
        r = TaskResult(task_id="task-a", success=True, duration_seconds=1.5)
        assert r.success
        assert r.task_id == "task-a"
        assert r.duration_seconds == 1.5
        assert r.error is None
        assert r.verify_result is None

    def test_failure_result(self):
        r = TaskResult(
            task_id="task-b",
            success=False,
            error="something broke",
            duration_seconds=3.0,
        )
        assert not r.success
        assert r.error == "something broke"


class TestDAGResult:
    """DAGResult tests."""

    def test_all_passed_when_all_success(self):
        r = DAGResult(
            dag_id="test",
            results=[
                TaskResult(task_id="a", success=True),
                TaskResult(task_id="b", success=True),
            ],
        )
        assert r.all_passed
        assert r.failed_tasks == []

    def test_all_passed_when_some_fail(self):
        r = DAGResult(
            dag_id="test",
            results=[
                TaskResult(task_id="a", success=True),
                TaskResult(task_id="b", success=False, error="fail"),
            ],
        )
        assert not r.all_passed
        assert r.failed_tasks == ["b"]

    def test_empty_results(self):
        r = DAGResult(dag_id="empty")
        assert r.all_passed
        assert r.failed_tasks == []

    def test_all_passed_with_global_verify_failure(self):
        """all_passed must be False when global_verify fails, even if all task results pass."""
        r = DAGResult(
            dag_id="gv-fail",
            results=[
                TaskResult(task_id="a", success=True),
                TaskResult(task_id="b", success=True),
            ],
            global_verify=ValidationResult(
                task_id="integration/gv-fail",
                passed=False,
                checks=[{"name": "make test", "passed": False, "detail": "3 tests failed"}],
            ),
        )
        assert not r.all_passed

    def test_all_passed_with_global_verify_success(self):
        """all_passed must be True when both tasks and global_verify pass."""
        r = DAGResult(
            dag_id="gv-ok",
            results=[
                TaskResult(task_id="a", success=True),
                TaskResult(task_id="b", success=True),
            ],
            global_verify=ValidationResult(
                task_id="integration/gv-ok",
                passed=True,
                checks=[{"name": "make test", "passed": True}],
            ),
        )
        assert r.all_passed


class TestFormatDAGSummary:
    """DAG summary formatting tests."""

    def test_foundation_task(self):
        dag = TaskDAG(dag_id="test-dag", tasks=[
            TaskNode(task_id="foundation-1", task_type="foundation"),
        ])
        output = _format_dag_summary(dag)
        assert "test-dag" in output
        assert "foundation-1" in output
        assert "Foundation" in output

    def test_all_task_types(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        output = _format_dag_summary(dag)
        assert "feature-agent-runtime-v2" in output
        assert "runtime-contract" in output
        assert "runtime-worker" in output
        assert "ui-panel" in output
        assert "integration-e2e" in output
        assert "Foundation" in output
        assert "Implementation" in output
        assert "Integration" in output
        assert "[parallel]" in output


class TestFormatResultsSummary:
    """Results summary formatting tests."""

    def test_all_passed(self):
        r = DAGResult(
            dag_id="dag-1",
            results=[
                TaskResult(task_id="a", success=True, duration_seconds=1.0),
                TaskResult(task_id="b", success=True, duration_seconds=2.0),
            ],
            total_duration_seconds=3.0,
        )
        output = _format_results_summary(r)
        assert "dag-1" in output
        assert "2 passed" in output
        assert "0 failed" in output

    def test_with_failures(self):
        r = DAGResult(
            dag_id="dag-2",
            results=[
                TaskResult(task_id="a", success=True, duration_seconds=1.0),
                TaskResult(task_id="b", success=False, error="test fail"),
            ],
            total_duration_seconds=2.0,
        )
        output = _format_results_summary(r)
        assert "1 passed" in output
        assert "1 failed" in output
        assert "test fail" in output
        assert "Fix" in output

    def test_with_integration_branch(self):
        r = DAGResult(
            dag_id="dag-3",
            results=[TaskResult(task_id="a", success=True)],
            integration_branch="integration/dag-3",
        )
        output = _format_results_summary(r)
        assert "integration/dag-3" in output


class TestGateStatus:
    """DAG gate status persistence tests."""

    def test_save_and_load_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            states_dir = Path(tmp)
            result = DAGResult(
                dag_id="dag-gate",
                results=[
                    TaskResult(task_id="a", success=True),
                    TaskResult(task_id="b", success=False, error="oops"),
                ],
                integration_branch="integration/dag-gate",
                global_verify=ValidationResult(task_id="dag-gate", passed=False, errors=["test failed"]),
            )
            # Use the static method directly
            gate_path = states_dir / "dag-dag-gate.json"
            gate_path.parent.mkdir(parents=True, exist_ok=True)
            gate_data = {
                "dag_id": result.dag_id,
                "all_passed": result.all_passed,
                "global_verify_passed": result.global_verify.passed if result.global_verify else False,
                "integration_branch": result.integration_branch,
                "tasks": [{"task_id": r.task_id, "success": r.success, "error": r.error} for r in result.results],
            }
            gate_path.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")

            loaded = DAGExecutor.load_gate_status("dag-gate", states_dir)
            assert loaded is not None
            assert loaded["dag_id"] == "dag-gate"
            assert loaded["global_verify_passed"] is False
            assert loaded["all_passed"] is False
            assert len(loaded["tasks"]) == 2

    def test_load_missing_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            assert DAGExecutor.load_gate_status("nonexistent", Path(tmp)) is None

    def test_all_passed_false_when_global_fails(self):
        r = DAGResult(
            dag_id="dag-fail",
            results=[TaskResult(task_id="a", success=True)],
            global_verify=ValidationResult(task_id="dag-fail", passed=False, errors=["test failed"]),
        )
        assert not r.all_passed


class TestGateUpdate:
    """DAG gate update after manual global verify."""

    def test_update_gate_flips_global_verify(self):
        from cli.verify import _update_dag_gate

        with tempfile.TemporaryDirectory() as tmp:
            states_dir = Path(tmp)
            gates_path = states_dir / "dag-mydag.json"
            gates_path.write_text(json.dumps({
                "dag_id": "mydag",
                "all_passed": False,
                "global_verify_passed": False,
                "tasks": [{"task_id": "a", "success": True}],
            }))

            _update_dag_gate("mydag", states_dir, passed=True)

            updated = json.loads(gates_path.read_text())
            assert updated["global_verify_passed"] is True
            assert updated["all_passed"] is True  # tasks all succeeded + global passed

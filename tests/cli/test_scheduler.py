"""Tests for cli.scheduler — DAG parsing and scheduling."""
from __future__ import annotations
from cli.scheduler import (
    TaskDAG,
    TaskNode,
    parse_dag_yaml,
    _detect_cycle,
    load_dag,
)


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


class TestTaskNode:
    """TaskNode tests."""

    def test_defaults(self):
        node = TaskNode(task_id="task-1")
        assert node.task_id == "task-1"
        assert node.task_type == "implementation"
        assert node.depends_on == []
        assert not node.parallelizable
        assert node.independent_verification


class TestParseDAGYAML:
    """DAG YAML parsing tests."""

    def test_parse_dag_id(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        assert dag.dag_id == "feature-agent-runtime-v2"

    def test_parse_all_tasks(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        assert len(dag.tasks) == 4
        task_ids = {t.task_id for t in dag.tasks}
        assert "runtime-contract" in task_ids
        assert "runtime-worker" in task_ids
        assert "ui-panel" in task_ids
        assert "integration-e2e" in task_ids

    def test_parse_task_types(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        by_id = {t.task_id: t for t in dag.tasks}
        assert by_id["runtime-contract"].task_type == "foundation"
        assert by_id["runtime-worker"].task_type == "implementation"
        assert by_id["integration-e2e"].task_type == "integration"

    def test_parse_dependencies(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        by_id = {t.task_id: t for t in dag.tasks}
        assert by_id["runtime-worker"].depends_on == ["runtime-contract"]
        assert by_id["ui-panel"].depends_on == ["runtime-contract"]
        assert by_id["integration-e2e"].depends_on == ["runtime-worker", "ui-panel"]
        assert by_id["runtime-contract"].depends_on == []

    def test_parse_parallelizable(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        by_id = {t.task_id: t for t in dag.tasks}
        assert not by_id["runtime-contract"].parallelizable
        assert by_id["runtime-worker"].parallelizable
        assert by_id["ui-panel"].parallelizable
        assert not by_id["integration-e2e"].parallelizable

    def test_empty_dag(self):
        dag = parse_dag_yaml("id: empty\n\ntasks: []")
        assert dag.dag_id == "empty"
        assert dag.tasks == []


class TestDAGValidation:
    """DAG validation tests."""

    def test_valid_dag_passes(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        errors = dag.validate()
        assert errors == []

    def test_missing_dependency(self):
        dag = TaskDAG(dag_id="bad", tasks=[
            TaskNode(task_id="a", depends_on=["nonexistent"]),
        ])
        errors = dag.validate()
        assert len(errors) > 0
        assert any("nonexistent" in e for e in errors)

    def test_foundation_cannot_be_parallel(self):
        dag = TaskDAG(dag_id="bad", tasks=[
            TaskNode(task_id="a", task_type="foundation", parallelizable=True),
        ])
        errors = dag.validate()
        assert len(errors) > 0
        assert any("foundation" in e.lower() for e in errors)

    def test_integration_cannot_independent_verify(self):
        dag = TaskDAG(dag_id="bad", tasks=[
            TaskNode(task_id="a", task_type="integration"),
        ])
        errors = dag.validate()
        assert len(errors) > 0
        assert any("integration" in e.lower() for e in errors)

    def test_cycle_detection(self):
        dag = TaskDAG(dag_id="cyclic", tasks=[
            TaskNode(task_id="a", depends_on=["b"]),
            TaskNode(task_id="b", depends_on=["a"]),
        ])
        errors = dag.validate()
        assert any("cycle" in e.lower() for e in errors)


class TestCycleDetection:
    """Cycle detection unit tests."""

    def test_no_cycle(self):
        nodes = [
            TaskNode(task_id="a", depends_on=["b"]),
            TaskNode(task_id="b", depends_on=[]),
        ]
        assert _detect_cycle(nodes) is None

    def test_simple_cycle(self):
        nodes = [
            TaskNode(task_id="a", depends_on=["b"]),
            TaskNode(task_id="b", depends_on=["a"]),
        ]
        result = _detect_cycle(nodes)
        assert result is not None

    def test_three_node_cycle(self):
        nodes = [
            TaskNode(task_id="a", depends_on=["b"]),
            TaskNode(task_id="b", depends_on=["c"]),
            TaskNode(task_id="c", depends_on=["a"]),
        ]
        result = _detect_cycle(nodes)
        assert result is not None


class TestDAGScheduling:
    """Task DAG scheduling tests."""

    def test_get_ready_tasks_none_completed(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        ready = dag.get_ready_tasks(set())
        assert len(ready) == 1
        assert ready[0].task_id == "runtime-contract"

    def test_get_ready_tasks_after_foundation(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        ready = dag.get_ready_tasks({"runtime-contract"})
        assert len(ready) == 2
        ids = {t.task_id for t in ready}
        assert ids == {"runtime-worker", "ui-panel"}

    def test_get_ready_tasks_after_implementation(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        ready = dag.get_ready_tasks({"runtime-contract", "runtime-worker", "ui-panel"})
        assert len(ready) == 1
        assert ready[0].task_id == "integration-e2e"

    def test_all_completed(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        all_ids = {t.task_id for t in dag.tasks}
        ready = dag.get_ready_tasks(all_ids)
        assert ready == []

    def test_parallel_groups(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        # After foundation, runtime-worker and ui-panel can run in parallel
        groups = dag.get_parallel_groups({"runtime-contract"})
        assert len(groups) == 1  # both parallelizable → same group
        ids = {t.task_id for t in groups[0]}
        assert ids == {"runtime-worker", "ui-panel"}

    def test_parallel_groups_foundation_alone(self):
        dag = parse_dag_yaml(SAMPLE_DAG_YAML)
        groups = dag.get_parallel_groups(set())
        assert len(groups) == 1
        assert groups[0][0].task_id == "runtime-contract"

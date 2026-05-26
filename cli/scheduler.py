"""
Task DAG and verifiability-aware scheduler.

Phase 2 MVP: parse a task graph (YAML), validate dependencies,
schedule parallel tasks when independent verification conditions are met.

Phase 1: architecture defined, implementation reserved for Phase 2.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TaskDAGError(Exception):
    """Raised when the task DAG is invalid."""
    pass


@dataclass
class TaskNode:
    task_id: str = ""
    task_type: str = "implementation"  # foundation | implementation | integration
    depends_on: list[str] = field(default_factory=list)
    parallelizable: bool = False
    independent_verification: bool = True
    state: str = "planned"


@dataclass
class TaskDAG:
    """A directed acyclic graph of tasks."""
    dag_id: str
    tasks: list[TaskNode] = field(default_factory=list)

    def validate(self) -> list[str]:
        """Validate the DAG for structural correctness."""
        errors: list[str] = []
        task_ids = {t.task_id for t in self.tasks}

        for task in self.tasks:
            # Check dependencies exist
            for dep in task.depends_on:
                if dep not in task_ids:
                    errors.append(f"Task '{task.task_id}' depends on unknown task '{dep}'")

            # Check type constraints
            if task.task_type == "foundation" and task.parallelizable:
                errors.append(f"Foundation task '{task.task_id}' cannot be parallelizable")
            if task.task_type == "integration" and task.independent_verification:
                errors.append(f"Integration task '{task.task_id}' cannot have independent_verification")

        # Check for cycles
        cycle = _detect_cycle(self.tasks)
        if cycle:
            errors.append(f"DAG has a cycle: {' -> '.join(cycle)}")

        return errors

    def get_ready_tasks(self, completed: set[str]) -> list[TaskNode]:
        """Get tasks whose dependencies are all satisfied."""
        ready = []
        for task in self.tasks:
            if task.task_id in completed:
                continue
            if all(dep in completed for dep in task.depends_on):
                ready.append(task)
        return ready

    def get_parallel_groups(self, completed: set[str]) -> list[list[TaskNode]]:
        """Group ready tasks into parallelizable batches.

        Returns groups where:
          - Each group contains tasks that can run in parallel
          - Foundation tasks form their own single-task groups
          - Implementation tasks that are parallelizable can share a group
          - Integration tasks run alone
        """
        ready = self.get_ready_tasks(completed)
        groups: list[list[TaskNode]] = []
        current_group: list[TaskNode] = []

        for task in ready:
            if task.task_type == "foundation" or not task.parallelizable:
                # Non-parallelizable tasks go alone
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([task])
            else:
                # Parallelizable implementation tasks can group together
                current_group.append(task)

        if current_group:
            groups.append(current_group)

        return groups


def _detect_cycle(tasks: list[TaskNode]) -> Optional[list[str]]:
    """Detect if there's a cycle in the DAG. Returns the cycle path or None."""
    task_map = {t.task_id: t for t in tasks}
    visited: set[str] = set()
    in_stack: set[str] = set()
    path: list[str] = []

    def dfs(node_id: str) -> Optional[list[str]]:
        visited.add(node_id)
        in_stack.add(node_id)
        path.append(node_id)

        task = task_map.get(node_id)
        if task:
            for dep in task.depends_on:
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in in_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

        path.pop()
        in_stack.discard(node_id)
        return None

    for task in tasks:
        if task.task_id not in visited:
            result = dfs(task.task_id)
            if result:
                return result

    return None


def parse_dag_yaml(text: str) -> TaskDAG:
    """Parse a YAML task graph definition. Returns a TaskDAG.

    Expected format:
    ```yaml
    id: feature-name
    tasks:
      - id: task-a
        type: foundation
        depends_on: []
        parallelizable: false
    ```
    """
    # Lightweight YAML parse — enough for the flat task structure
    import re

    dag_id = ""
    tasks: list[TaskNode] = []

    lines = text.strip().splitlines()
    current_task: Optional[dict] = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level id
        if stripped.startswith("id:") and ":" in stripped:
            dag_id = stripped.partition(":")[2].strip().strip('"')
            continue

        # Task start
        if stripped.startswith("- id:"):
            if current_task:
                tasks.append(_build_node(current_task))
            task_name = stripped.partition(":")[2].strip().strip('"')
            current_task = {"id": task_name}
            continue

        if current_task is not None:
            if stripped.startswith("type:"):
                current_task["type"] = _parse_yaml_value(stripped)
            elif stripped.startswith("depends_on:"):
                # Could be inline list or multi-line
                val = _parse_yaml_value(stripped)
                if val and val != "[]":
                    # Inline list: [a, b]
                    items = [v.strip().strip('"') for v in val.strip("[]").split(",") if v.strip()]
                    current_task["depends_on"] = items
                else:
                    current_task["depends_on"] = []
            elif stripped.startswith("- ") and current_task.get("depends_on") == []:
                # Multi-line depends_on list item
                dep = stripped[2:].strip().strip('"')
                current_task.setdefault("_depends", []).append(dep)
            elif stripped.startswith("parallelizable:"):
                current_task["parallelizable"] = _parse_yaml_value(stripped) in ("true", "True")
            elif stripped.startswith("independent_verification:"):
                current_task["independent_verification"] = _parse_yaml_value(stripped) in ("true", "True")

    if current_task:
        tasks.append(_build_node(current_task))

    return TaskDAG(dag_id=dag_id, tasks=tasks)


def _parse_yaml_value(line: str) -> str:
    """Extract value from 'key: value' line."""
    if ":" in line:
        return line.partition(":")[2].strip().strip('"').strip("'")
    return ""


def _build_node(data: dict) -> TaskNode:
    """Build a TaskNode from parsed dict data."""
    depends = data.get("depends_on", [])
    if data.get("_depends"):
        depends = data["_depends"]
    return TaskNode(
        task_id=data["id"],
        task_type=data.get("type", "implementation"),
        depends_on=depends,
        parallelizable=data.get("parallelizable", False),
        independent_verification=data.get("independent_verification", True),
    )


def load_dag(path: Path) -> Optional[TaskDAG]:
    """Load a DAG from a YAML file."""
    try:
        text = path.read_text(encoding="utf-8")
        return parse_dag_yaml(text)
    except (FileNotFoundError, OSError):
        return None

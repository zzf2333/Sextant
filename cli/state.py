"""
Task state machine — defines the 14 states a task can be in
and the valid transitions between them.

State is persisted as a flat JSON file in the worktree metadata directory.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import json
from typing import Optional


class TaskState(Enum):
    """Task lifecycle states."""
    PLANNED = "planned"
    WORKTREE_CREATED = "worktree_created"
    EXECUTING = "executing"
    LOCAL_VERIFYING = "local_verifying"
    LOCAL_VERIFIED = "local_verified"
    LOCAL_FAILED = "local_failed"
    QUEUED_FOR_INTEGRATION = "queued_for_integration"
    INTEGRATED = "integrated"
    GLOBAL_VERIFYING = "global_verifying"
    GLOBAL_VERIFIED = "global_verified"
    GLOBAL_FAILED = "global_failed"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    MERGED = "merged"
    CANCELLED = "cancelled"
    FAILED = "failed"


# Valid transitions — a task can only move to states in this set
_VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PLANNED: {TaskState.WORKTREE_CREATED, TaskState.CANCELLED},
    TaskState.WORKTREE_CREATED: {TaskState.EXECUTING, TaskState.CANCELLED},
    TaskState.EXECUTING: {TaskState.LOCAL_VERIFYING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.LOCAL_VERIFYING: {TaskState.LOCAL_VERIFIED, TaskState.LOCAL_FAILED},
    TaskState.LOCAL_VERIFIED: {TaskState.REVIEWING, TaskState.QUEUED_FOR_INTEGRATION, TaskState.CANCELLED},
    TaskState.LOCAL_FAILED: {TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.QUEUED_FOR_INTEGRATION: {TaskState.INTEGRATED, TaskState.CANCELLED},
    TaskState.INTEGRATED: {TaskState.GLOBAL_VERIFYING, TaskState.CANCELLED},
    TaskState.GLOBAL_VERIFYING: {TaskState.GLOBAL_VERIFIED, TaskState.GLOBAL_FAILED},
    TaskState.GLOBAL_VERIFIED: {TaskState.REVIEWING, TaskState.QUEUED_FOR_INTEGRATION},  # allow re-queue from global verify
    TaskState.GLOBAL_FAILED: {TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.REVIEWING: {TaskState.APPROVED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.APPROVED: {TaskState.MERGED},
    TaskState.MERGED: set(),       # terminal
    TaskState.CANCELLED: set(),    # terminal
    TaskState.FAILED: set(),       # terminal
}

# States where execution has stopped (terminal or paused)
TERMINAL_STATES: frozenset[TaskState] = frozenset({
    TaskState.MERGED,
    TaskState.CANCELLED,
    TaskState.FAILED,
})

# States where the task is in progress
ACTIVE_STATES: frozenset[TaskState] = frozenset({
    TaskState.PLANNED,
    TaskState.WORKTREE_CREATED,
    TaskState.EXECUTING,
    TaskState.LOCAL_VERIFYING,
    TaskState.LOCAL_FAILED,
    TaskState.LOCAL_VERIFIED,
    TaskState.QUEUED_FOR_INTEGRATION,
    TaskState.INTEGRATED,
    TaskState.GLOBAL_VERIFYING,
    TaskState.GLOBAL_FAILED,
    TaskState.GLOBAL_VERIFIED,
    TaskState.REVIEWING,
    TaskState.APPROVED,
})


@dataclass
class TaskStateRecord:
    task_id: str
    state: TaskState = TaskState.PLANNED
    state_history: list[dict] = field(default_factory=list)  # [{state, timestamp, reason}]
    worktree_path: Optional[str] = None
    contract_path: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None

    def can_transition_to(self, target: TaskState) -> bool:
        return target in _VALID_TRANSITIONS.get(self.state, set())

    def transition_to(self, target: TaskState, reason: str = "") -> None:
        """Transition to a new state. Raises ValueError if invalid."""
        if not self.can_transition_to(target):
            raise ValueError(
                f"Invalid state transition: {self.state.value} -> {target.value}"
            )
        from datetime import datetime, timezone
        self.state_history.append({
            "from": self.state.value,
            "to": target.value,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "reason": reason,
        })
        self.state = target


def load_state(state_dir: Path, task_id: str) -> TaskStateRecord:
    """Load task state from a JSON file."""
    state_path = state_dir / f"{task_id}.json"
    if not state_path.exists():
        return TaskStateRecord(task_id=task_id, state=TaskState.PLANNED)

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return TaskStateRecord(
            task_id=data["task_id"],
            state=TaskState(data["state"]),
            state_history=data.get("state_history", []),
            worktree_path=data.get("worktree_path"),
            contract_path=data.get("contract_path"),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        return TaskStateRecord(
            task_id=task_id,
            state=TaskState.FAILED,
            last_error=f"Failed to parse state file: {e}",
        )


def save_state(state_dir: Path, record: TaskStateRecord) -> None:
    """Persist task state to a JSON file."""
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / f"{record.task_id}.json"
    data = {
        "task_id": record.task_id,
        "state": record.state.value,
        "state_history": record.state_history,
        "worktree_path": record.worktree_path,
        "contract_path": record.contract_path,
        "error_count": record.error_count,
        "last_error": record.last_error,
    }
    state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_active_tasks(state_dir: Path) -> list[TaskStateRecord]:
    """List all tasks that are in active (non-terminal) states."""
    if not state_dir.exists():
        return []
    records = []
    for f in state_dir.glob("*.json"):
        task_id = f.stem
        record = load_state(state_dir, task_id)
        if record.state in ACTIVE_STATES:
            records.append(record)
    return records


def format_state(record: TaskStateRecord) -> str:
    """Format a TaskStateRecord for display."""
    history_str = ""
    if record.state_history:
        last = record.state_history[-1]
        history_str = f"  (last: {last['from']} -> {last['to']}, reason: {last['reason'][:60]})"

    lines = [
        f"Task:      {record.task_id}",
        f"State:     {record.state.value}{history_str}",
        f"Worktree:  {record.worktree_path or 'not created'}",
        f"Errors:    {record.error_count}",
    ]
    if record.last_error:
        lines.append(f"Last err:  {record.last_error[:120]}")
    return "\n".join(lines)

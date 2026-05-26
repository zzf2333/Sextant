"""Tests for cli.state — task state machine."""
from __future__ import annotations
import json
import tempfile
import pytest
from pathlib import Path

from cli.state import (
    TaskState,
    TaskStateRecord,
    load_state,
    save_state,
    list_active_tasks,
    format_state,
    TERMINAL_STATES,
    ACTIVE_STATES,
)


class TestTaskState:
    """TaskState enum tests."""

    def test_all_states_defined(self):
        assert TaskState.PLANNED.value == "planned"
        assert TaskState.MERGED.value == "merged"

    def test_terminal_states(self):
        assert TaskState.MERGED in TERMINAL_STATES
        assert TaskState.CANCELLED in TERMINAL_STATES
        assert TaskState.FAILED in TERMINAL_STATES
        assert TaskState.PLANNED not in TERMINAL_STATES

    def test_active_states(self):
        assert TaskState.PLANNED in ACTIVE_STATES
        assert TaskState.EXECUTING in ACTIVE_STATES
        assert TaskState.MERGED not in ACTIVE_STATES


class TestTaskStateRecord:
    """TaskStateRecord tests."""

    def test_default_state_is_planned(self):
        record = TaskStateRecord(task_id="task-1")
        assert record.state == TaskState.PLANNED
        assert record.state_history == []

    def test_can_transition_valid(self):
        record = TaskStateRecord(task_id="task-1")
        assert record.can_transition_to(TaskState.WORKTREE_CREATED)
        assert record.can_transition_to(TaskState.CANCELLED)

    def test_can_transition_invalid(self):
        record = TaskStateRecord(task_id="task-1")
        assert not record.can_transition_to(TaskState.EXECUTING)
        assert not record.can_transition_to(TaskState.MERGED)

    def test_transition_to_valid(self):
        record = TaskStateRecord(task_id="task-1")
        record.transition_to(TaskState.WORKTREE_CREATED, "worktree created")
        assert record.state == TaskState.WORKTREE_CREATED
        assert len(record.state_history) == 1
        assert record.state_history[0]["from"] == "planned"
        assert record.state_history[0]["to"] == "worktree_created"
        assert record.state_history[0]["reason"] == "worktree created"

    def test_transition_to_invalid_raises(self):
        record = TaskStateRecord(task_id="task-1")
        try:
            record.transition_to(TaskState.MERGED)
            assert False, "should have raised ValueError"
        except ValueError:
            pass

    def test_full_lifecycle_with_review(self):
        """Test the single-task lifecycle: LOCAL_VERIFIED -> REVIEWING -> APPROVED -> MERGED."""
        record = TaskStateRecord(task_id="task-r")
        transitions = [
            (TaskState.WORKTREE_CREATED, "created"),
            (TaskState.EXECUTING, "executing"),
            (TaskState.LOCAL_VERIFYING, "verifying"),
            (TaskState.LOCAL_VERIFIED, "local ok"),
            (TaskState.REVIEWING, "review started"),  # LOCAL_VERIFIED → REVIEWING
            (TaskState.APPROVED, "review approved"),
            (TaskState.MERGED, "merged"),
        ]
        for state, reason in transitions:
            record.transition_to(state, reason)
        assert record.state == TaskState.MERGED

    def test_reviewing_self_transition_rejected(self):
        """REVIEWING → REVIEWING self-transition must be rejected."""
        record = TaskStateRecord(task_id="task-s")
        record.transition_to(TaskState.WORKTREE_CREATED, "created")
        record.transition_to(TaskState.EXECUTING, "executing")
        record.transition_to(TaskState.LOCAL_VERIFYING, "verifying")
        record.transition_to(TaskState.LOCAL_VERIFIED, "local ok")
        record.transition_to(TaskState.REVIEWING, "review started")
        with pytest.raises(ValueError, match="Invalid state transition"):
            record.transition_to(TaskState.REVIEWING, "still reviewing")

    def test_reviewing_to_local_failed(self):
        """REVIEWING → LOCAL_FAILED must be allowed (changes-requested from review)."""
        record = TaskStateRecord(task_id="task-cr")
        record.transition_to(TaskState.WORKTREE_CREATED, "created")
        record.transition_to(TaskState.EXECUTING, "executing")
        record.transition_to(TaskState.LOCAL_VERIFYING, "verifying")
        record.transition_to(TaskState.LOCAL_VERIFIED, "local ok")
        record.transition_to(TaskState.REVIEWING, "review started")
        record.transition_to(TaskState.LOCAL_FAILED, "changes requested")
        assert record.state == TaskState.LOCAL_FAILED

    def test_reviewing_to_approved(self):
        """REVIEWING → APPROVED must be allowed."""
        record = TaskStateRecord(task_id="task-ok")
        record.transition_to(TaskState.WORKTREE_CREATED, "created")
        record.transition_to(TaskState.EXECUTING, "executing")
        record.transition_to(TaskState.LOCAL_VERIFYING, "verifying")
        record.transition_to(TaskState.LOCAL_VERIFIED, "local ok")
        record.transition_to(TaskState.REVIEWING, "review started")
        record.transition_to(TaskState.APPROVED, "approved")
        assert record.state == TaskState.APPROVED


class TestStatePersistence:
    """State save/load tests."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            record = TaskStateRecord(
                task_id="task-abc",
                state=TaskState.EXECUTING,
                worktree_path="/tmp/wt",
                error_count=2,
                last_error="something went wrong",
            )
            record.state_history.append({
                "from": "planned",
                "to": "executing",
                "timestamp": "2026-01-01T00:00:00Z",
                "reason": "test",
            })

            save_state(state_dir, record)
            loaded = load_state(state_dir, "task-abc")

            assert loaded.task_id == "task-abc"
            assert loaded.state == TaskState.EXECUTING
            assert loaded.worktree_path == "/tmp/wt"
            assert loaded.error_count == 2
            assert loaded.last_error == "something went wrong"
            assert len(loaded.state_history) == 1

    def test_load_missing_returns_planned(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            record = load_state(state_dir, "nonexistent")
            assert record.task_id == "nonexistent"
            assert record.state == TaskState.PLANNED

    def test_list_active_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            # Create active task
            active = TaskStateRecord(task_id="active-1", state=TaskState.EXECUTING)
            save_state(state_dir, active)
            # Create terminal task
            terminal = TaskStateRecord(task_id="done-1", state=TaskState.MERGED)
            save_state(state_dir, terminal)

            active_list = list_active_tasks(state_dir)
            assert len(active_list) == 1
            assert active_list[0].task_id == "active-1"


class TestFormatState:
    """format_state tests."""

    def test_basic_output(self):
        record = TaskStateRecord(task_id="my-task")
        output = format_state(record)
        assert "my-task" in output
        assert "planned" in output

    def test_with_history(self):
        record = TaskStateRecord(task_id="t1")
        record.transition_to(TaskState.WORKTREE_CREATED, "created")
        record.transition_to(TaskState.EXECUTING, "started work")
        output = format_state(record)
        assert "executing" in output
        assert "started work" in output

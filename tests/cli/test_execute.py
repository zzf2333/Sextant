"""Tests for cli.execute — single-task execution flow."""
from __future__ import annotations
from argparse import Namespace
from pathlib import Path

import pytest

from cli.execute import run_execute
from cli.state import TaskState, load_state
from cli.validator import ValidationResult


def _write_contract(traces_dir: Path, task_id: str) -> None:
    """Write a minimal valid TASK_CONTRACT.md."""
    trace_dir = traces_dir / task_id
    trace_dir.mkdir(parents=True)
    (trace_dir / "TASK_CONTRACT.md").write_text("""# TASK_CONTRACT

## Metadata

```yaml
task_id: "{task_id}"
task_type: "implementation"
depends_on: []
parallelizable: false
independent_verification: true
```

---

## objective

test

---

## allowed_paths

```yaml
allowed_paths:
  - src/**
```

---

## forbidden_paths

```yaml
forbidden_paths:
```

---

## constraints

- none

---

## acceptance

- [ ] true
""".replace("{task_id}", task_id))


class _FakeWorktree:
    """Minimal worktree stub for monkeypatching."""
    path: Path
    branch: str

    def __init__(self, path: Path, branch: str = "sextant/task/fake"):
        self.path = path
        self.branch = branch


class TestExecuteExitCode:
    """sextant execute exit code semantics."""

    def test_validator_failure_returns_1(self, tmp_path, monkeypatch):
        """When local verify fails → exit code 1."""
        traces = tmp_path / "traces"
        states = tmp_path / "states"
        worktrees = tmp_path / "worktrees"
        task_id = "task-1"
        _write_contract(traces, task_id)

        wt = _FakeWorktree(tmp_path / "wt")
        wt.path.mkdir()

        monkeypatch.setattr("cli.execute.create_worktree", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute.get_worktree_info", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute._execute_reasonix", lambda *a, **k: None)
        monkeypatch.setattr(
            "cli.validator.validate_contract",
            lambda *a, **k: ValidationResult(
                task_id=task_id, passed=False,
                checks=[{"name": "forbidden_paths", "passed": False, "detail": "violation"}],
            ),
        )

        args = Namespace(
            task_id=task_id, contract_path=None, base_branch="main",
            worktrees_dir=str(worktrees), traces_dir=str(traces),
            states_dir=str(states), runtime="reasonix", dry_run=False,
        )
        rc = run_execute(args)
        assert rc == 1

    def test_commit_failure_returns_1(self, tmp_path, monkeypatch):
        """When verify passes but commit fails → exit code 1."""
        traces = tmp_path / "traces"
        states = tmp_path / "states"
        worktrees = tmp_path / "worktrees"
        task_id = "task-2"
        _write_contract(traces, task_id)

        wt = _FakeWorktree(tmp_path / "wt")
        wt.path.mkdir()

        monkeypatch.setattr("cli.execute.create_worktree", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute.get_worktree_info", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute._execute_reasonix", lambda *a, **k: None)
        monkeypatch.setattr(
            "cli.validator.validate_contract",
            lambda *a, **k: ValidationResult(task_id=task_id, passed=True),
        )
        monkeypatch.setattr(
            "cli.execute.commit_worker_changes",
            lambda *a, **k: (False, "pre-commit hook blocked"),
        )

        args = Namespace(
            task_id=task_id, contract_path=None, base_branch="main",
            worktrees_dir=str(worktrees), traces_dir=str(traces),
            states_dir=str(states), runtime="reasonix", dry_run=False,
        )
        rc = run_execute(args)
        assert rc == 1

    def test_commit_failure_sets_state_local_failed(self, tmp_path, monkeypatch):
        """Commit failure → state file records LOCAL_FAILED + last_error."""
        traces = tmp_path / "traces"
        states = tmp_path / "states"
        worktrees = tmp_path / "worktrees"
        task_id = "task-3"
        _write_contract(traces, task_id)

        wt = _FakeWorktree(tmp_path / "wt")
        wt.path.mkdir()

        monkeypatch.setattr("cli.execute.create_worktree", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute.get_worktree_info", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute._execute_reasonix", lambda *a, **k: None)
        monkeypatch.setattr(
            "cli.validator.validate_contract",
            lambda *a, **k: ValidationResult(task_id=task_id, passed=True),
        )
        monkeypatch.setattr(
            "cli.execute.commit_worker_changes",
            lambda *a, **k: (False, "identity missing"),
        )

        args = Namespace(
            task_id=task_id, contract_path=None, base_branch="main",
            worktrees_dir=str(worktrees), traces_dir=str(traces),
            states_dir=str(states), runtime="reasonix", dry_run=False,
        )
        rc = run_execute(args)

        assert rc == 1
        state = load_state(states, task_id)
        assert state.state == TaskState.LOCAL_FAILED
        assert "commit failed" in state.last_error

    def test_local_verified_returns_0(self, tmp_path, monkeypatch):
        """Verify passes + commit succeeds → exit code 0, state LOCAL_VERIFIED."""
        traces = tmp_path / "traces"
        states = tmp_path / "states"
        worktrees = tmp_path / "worktrees"
        task_id = "task-4"
        _write_contract(traces, task_id)

        wt = _FakeWorktree(tmp_path / "wt")
        wt.path.mkdir()

        monkeypatch.setattr("cli.execute.create_worktree", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute.get_worktree_info", lambda *a, **k: wt)
        monkeypatch.setattr("cli.execute._execute_reasonix", lambda *a, **k: None)
        monkeypatch.setattr(
            "cli.validator.validate_contract",
            lambda *a, **k: ValidationResult(task_id=task_id, passed=True),
        )
        monkeypatch.setattr(
            "cli.execute.commit_worker_changes",
            lambda *a, **k: (True, "committed"),
        )

        args = Namespace(
            task_id=task_id, contract_path=None, base_branch="main",
            worktrees_dir=str(worktrees), traces_dir=str(traces),
            states_dir=str(states), runtime="reasonix", dry_run=False,
        )
        rc = run_execute(args)

        assert rc == 0
        state = load_state(states, task_id)
        assert state.state == TaskState.LOCAL_VERIFIED

    def test_dry_run_returns_0(self, tmp_path, monkeypatch):
        """Dry-run always returns 0 regardless of state."""
        traces = tmp_path / "traces"
        states = tmp_path / "states"
        worktrees = tmp_path / "worktrees"
        task_id = "task-5"
        _write_contract(traces, task_id)

        args = Namespace(
            task_id=task_id, contract_path=None, base_branch="main",
            worktrees_dir=str(worktrees), traces_dir=str(traces),
            states_dir=str(states), runtime="reasonix", dry_run=True,
        )
        rc = run_execute(args)
        assert rc == 0

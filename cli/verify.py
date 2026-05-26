"""
sextant verify — run deterministic verification against a task's worktree.

Runs:
  1. forbidden_path check
  2. diff_size check
  3. dependency_drift check
  4. acceptance command execution
  5. Global verify (if integration branch exists)
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

from cli.state import (
    TaskState,
    load_state,
    save_state,
    format_state,
)
from cli.validator import validate_contract, format_validation


def run_verify(args) -> int:
    task_id = getattr(args, "task_id", None)
    worktrees_dir = Path(getattr(args, "worktrees_dir", ".sextant-worktrees")).resolve()
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()
    global_verify = getattr(args, "global", False)

    if not task_id:
        # Verify all active worktrees
        from cli.worktree import list_worktrees
        worktrees = list_worktrees(worktrees_dir)
        if not worktrees:
            print("No active worktrees found.")
            return 0

        print(f"Verifying {len(worktrees)} worktree(s)...\n")
        all_passed = True
        for wt in worktrees:
            result = validate_contract(wt.task_id, worktrees_dir)
            print(format_validation(result))
            print("")
            if not result.passed:
                all_passed = False

        return 0 if all_passed else 1

    # Verify single task
    state = load_state(states_dir, task_id)

    if global_verify:
        print(f"Global verification for: {task_id}")
        state.transition_to(TaskState.GLOBAL_VERIFYING, "global verify started")
        save_state(states_dir, state)
    else:
        print(f"Local verification for: {task_id}")
        state.transition_to(TaskState.LOCAL_VERIFYING, "local verify started")
        save_state(states_dir, state)

    result = validate_contract(task_id, worktrees_dir)
    print(format_validation(result))

    if result.passed:
        if global_verify:
            state.transition_to(TaskState.GLOBAL_VERIFIED, "global verify passed")
        else:
            state.transition_to(TaskState.LOCAL_VERIFIED, "local verify passed")
    else:
        state.error_count += 1
        state.last_error = f"{result.error_count} check(s) failed"
        if global_verify:
            state.transition_to(TaskState.GLOBAL_FAILED, "global verify failed")
        else:
            state.transition_to(TaskState.LOCAL_FAILED, "local verify failed")
    save_state(states_dir, state)

    print("")
    print(format_state(state))
    print("")
    print("  Next:")
    if state.state in (TaskState.LOCAL_VERIFIED, TaskState.GLOBAL_VERIFIED):
        print(f"    sextant review --task-id {task_id}")
    else:
        print(f"    Fix errors and re-run: sextant verify --task-id {task_id}")

    return 0 if result.passed else 1

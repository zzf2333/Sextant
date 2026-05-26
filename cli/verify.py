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

        # Global verify = run test command on integration branch, not single-worktree
        result = run_global_verify_integration(task_id)
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


# ── Global verify helpers ─────────────────────────────────────────────

def run_global_verify_integration(dag_id: str) -> "ValidationResult":
    """Run global verification on the integration branch.

    Checks out integration/<dag_id>, runs detected project tests,
    and restores the original branch afterward. Returns a ValidationResult.
    """
    import subprocess
    from cli.worktree import get_repo_root, has_uncommitted_changes

    repo_root = get_repo_root()
    integration_branch = f"integration/{dag_id}"
    original_branch = None
    all_checks: list[dict] = []

    try:
        # Get current branch for restore
        ref = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        original_branch = ref.stdout.strip()

        # Verify integration branch exists
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", integration_branch],
                cwd=repo_root, capture_output=True, text=True, timeout=10,
            ).check_returncode()
        except subprocess.CalledProcessError:
            from cli.validator import ValidationResult
            return ValidationResult(
                task_id=dag_id,
                passed=False,
                errors=[
                    f"Integration branch '{integration_branch}' not found. "
                    "Run 'sextant run' first."
                ],
            )

        # Checkout integration branch
        if has_uncommitted_changes(repo_root):
            from cli.validator import ValidationResult
            return ValidationResult(
                task_id=dag_id,
                passed=False,
                errors=["Uncommitted changes — stash or commit before global verify."],
            )

        subprocess.run(
            ["git", "checkout", integration_branch],
            cwd=repo_root, capture_output=True, text=True, timeout=30,
        ).check_returncode()

        # Run detected test commands
        test_cmds = _detect_test_commands(repo_root)
        all_passed = True

        for cmd in test_cmds:
            proc = subprocess.run(
                cmd, cwd=repo_root, capture_output=True,
                text=True, timeout=120, shell=True,
            )
            passed = proc.returncode == 0
            detail = f"exit {proc.returncode}"
            if not passed:
                stderr_tail = proc.stderr.strip()
                if stderr_tail:
                    detail += f" | {stderr_tail[-150:]}"
                all_passed = False
            all_checks.append({"name": cmd, "passed": passed, "detail": detail})
            print(f"      {'✓' if passed else '✗'} {cmd}")

        from cli.validator import ValidationResult
        return ValidationResult(
            task_id=dag_id,
            passed=all_passed,
            checks=all_checks,
        )

    except Exception as e:
        from cli.validator import ValidationResult
        return ValidationResult(
            task_id=dag_id,
            passed=False,
            errors=[str(e)],
        )
    finally:
        if original_branch:
            try:
                subprocess.run(
                    ["git", "checkout", original_branch],
                    cwd=repo_root, capture_output=True, text=True, timeout=30,
                )
            except Exception:
                pass


def _detect_test_commands(repo_root: Path) -> list[str]:
    """Detect test commands from common project files."""
    cmds: list[str] = []
    if (repo_root / "package.json").exists():
        cmds.append("npm test 2>&1")
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        cmds.append("python3 -m pytest 2>&1")
    if (repo_root / "Makefile").exists():
        cmds.append("make test 2>&1")
    if (repo_root / "go.mod").exists():
        cmds.append("go test ./... 2>&1")
    if (repo_root / "Cargo.toml").exists():
        cmds.append("cargo test 2>&1")
    if not cmds:
        cmds.append("echo '(no test commands detected)'")
    return cmds

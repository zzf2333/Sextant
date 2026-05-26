"""
sextant execute — execute a task in an isolated git worktree.

This is the core of Sextant v2:
  1. Create a git worktree for the task
  2. Copy TASK_CONTRACT.md into the worktree
  3. Invoke the Executor (Reasonix Worker or other) with the contract
  4. Track state transitions

The Executor receives:
  - The worktree directory (isolated filesystem context)
  - TASK_CONTRACT.md (bounded context)
  - No other project context
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from cli.contract import TaskContract, parse_contract, generate_contract
from cli.state import (
    TaskState,
    TaskStateRecord,
    load_state,
    save_state,
    format_state,
)
from cli.worktree import (
    WorktreeError,
    WorktreeInfo,
    create_worktree,
    remove_worktree,
    get_worktree_info,
)


def run_execute(args) -> int:
    task_id = getattr(args, "task_id", None)
    contract_path = getattr(args, "contract_path", None)
    base_branch = getattr(args, "base_branch", "main")
    worktrees_dir = (
        Path(getattr(args, "worktrees_dir", ".sextant-worktrees")).resolve()
    )
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces")).resolve()
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()
    runtime = getattr(args, "runtime", "reasonix")
    dry_run = getattr(args, "dry_run", False)

    if not task_id:
        print("Usage: sextant execute --task-id <id> [--contract-path <path>]")
        print("")
        print("  Execute a task in an isolated git worktree.")
        print("  Options:")
        print("    --contract-path  Path to TASK_CONTRACT.md (default: .sextant/traces/<id>/TASK_CONTRACT.md)")
        print("    --base-branch    Base branch for worktree (default: main)")
        print("    --runtime        Executor runtime: reasonix (default)")
        print("    --dry-run        Show what would happen without executing")
        return 1

    # Load or create state
    state = load_state(states_dir, task_id)

    # Resolve contract
    contract: Optional[TaskContract] = None
    if contract_path:
        contract = parse_contract(Path(contract_path))
    else:
        # Look for contract in traces directory
        candidate = traces_dir / task_id / "TASK_CONTRACT.md"
        if candidate.exists():
            contract = parse_contract(candidate)

    if contract is None:
        print(f"  No TASK_CONTRACT.md found for task '{task_id}'.")
        print("  Run 'sextant plan --task-id", task_id, "' first.")
        return 1

    # Validate contract
    errors = contract.validate()
    if errors:
        print("  Contract validation failed:")
        for e in errors:
            print(f"    - {e}")
        return 1

    print(f"Task:        {task_id}")
    print(f"Objective:   {contract.objective[:80]}")
    print(f"Type:        {contract.task_type}")
    print(f"Runtime:     {runtime}")
    print(f"Base branch: {base_branch}")
    print("")

    # ── Phase 1: Create worktree ──
    print("  [1/4] Creating worktree...")
    if dry_run:
        print(f"    (dry-run) Would create worktree at .sextant-worktrees/{task_id}")
    else:
        try:
            wt = create_worktree(task_id, base_branch, worktrees_dir)
            state.worktree_path = str(wt.path)
            state.contract_path = str(contract_path) if contract_path else str(
                traces_dir / task_id / "TASK_CONTRACT.md"
            )
            state.transition_to(TaskState.WORKTREE_CREATED, "worktree created")
            save_state(states_dir, state)
            print(f"    Created: {wt.path}")
            print(f"    Branch:  {wt.branch}")
        except WorktreeError as e:
            print(f"    Error: {e}")
            return 1

    # ── Phase 2: Copy contract to worktree ──
    print("  [2/4] Deploying TASK_CONTRACT.md to worktree...")
    if not dry_run:
        wt = get_worktree_info(task_id, worktrees_dir)
        if wt:
            dest = wt.path / "TASK_CONTRACT.md"
            dest.write_text(contract.to_markdown(), encoding="utf-8")
            print(f"    Written: {dest}")

    # ── Phase 3: Execute ──
    print("  [3/4] Starting execution...")
    if dry_run:
        print(f"    (dry-run) Would start {runtime} Worker in worktree")
    else:
        state.transition_to(TaskState.EXECUTING, f"execution started with {runtime}")
        save_state(states_dir, state)

        if runtime == "reasonix":
            _execute_reasonix(task_id, contract, worktrees_dir)
        else:
            print(f"    Unknown runtime: {runtime}")
            print("    Supported: reasonix")
            return 1

    # ── Phase 4: Local verify ──
    print("  [4/4] Running local verification...")
    if dry_run:
        print("    (dry-run) Would run: sextant verify --task-id", task_id)
    else:
        state.transition_to(TaskState.LOCAL_VERIFYING, "local verify started")
        save_state(states_dir, state)

        # Run validator
        try:
            from cli.validator import validate_contract, format_validation
            result = validate_contract(task_id, worktrees_dir)
            print(format_validation(result))

            if result.passed:
                state.transition_to(TaskState.LOCAL_VERIFIED, "all checks passed")
            else:
                state.error_count += 1
                state.last_error = f"{result.error_count} validation check(s) failed"
                state.transition_to(TaskState.LOCAL_FAILED, "validation failed")
            save_state(states_dir, state)
        except Exception as e:
            state.error_count += 1
            state.last_error = str(e)
            state.transition_to(TaskState.LOCAL_FAILED, f"validation error: {e}")
            save_state(states_dir, state)

    print("")
    print(format_state(state))
    print("")
    print("  Next:")
    if state.state == TaskState.LOCAL_VERIFIED:
        print(f"    sextant verify --task-id {task_id}  (global verify)")
        print(f"    sextant review --task-id {task_id}")
        print(f"    sextant merge --task-id {task_id}")
    elif state.state == TaskState.LOCAL_FAILED:
        print(f"    Fix errors in worktree, then re-run:")
        print(f"    sextant execute --task-id {task_id}")
    else:
        print(f"    sextant status")
    return 0


def _execute_reasonix(
    task_id: str,
    contract: TaskContract,
    worktrees_dir: Path,
) -> None:
    """Invoke a Reasonix Worker in the worktree.

    The Worker receives:
      - TASK_CONTRACT.md (already in worktree)
      - allowed_paths as the only modifiable files
      - No other project context
    """
    wt = get_worktree_info(task_id, worktrees_dir)
    if wt is None:
        print("    Error: worktree not found after creation")
        return

    # Write execution instructions
    instructions = wt.path / "EXECUTOR_INSTRUCTIONS.md"
    constraints_str = "\n".join(f"- {c}" for c in contract.constraints)
    allowed_str = "\n".join(f"- {p}" for p in contract.allowed_paths)
    acceptance_str = "\n".join(f"- {c}" for c in contract.acceptance)

    instructions.write_text(f"""# Executor Instructions

You are a Reasonix Worker. Your only context is this worktree.

## Task
{contract.objective}

## Contract
Read TASK_CONTRACT.md for full details. Key constraints:

**Allowed paths (only modify these):**
{allowed_str}

**Constraints:**
{constraints_str}

**Acceptance criteria:**
{acceptance_str}

## Rules
1. Do NOT expand scope beyond the contract
2. Do NOT modify files outside allowed_paths
3. Do NOT add new dependencies without contract authorization
4. Read TASK_CONTRACT.md before starting
5. When done, confirm all acceptance criteria are met

## Verification
After completion, the system runs:
  sextant verify --task-id {task_id}
""", encoding="utf-8")

    print(f"    Reasonix Worker instructions written to: {instructions}")
    print(f"    Worker should now read TASK_CONTRACT.md and EXECUTOR_INSTRUCTIONS.md")
    print(f"    in the worktree at: {wt.path}")

"""
sextant review — invoke a Reviewer (Claude/Codex) to review a task's output.

The Reviewer receives a Clean Context Packet:
  - TASK_CONTRACT.md
  - Build diff (from worktree)
  - Verification results
  - Review rubric (core/roles/reviewer.md + core/templates/review.md)

Supports automated review backends:
  - file: write prompt to file for manual review (default)
  - claude: invoke Claude CLI
  - codex: invoke Codex CLI (future)
"""
from __future__ import annotations
import sys
from pathlib import Path

from cli.state import (
    TaskState,
    load_state,
    save_state,
    format_state,
)
from cli.worktree import get_worktree_info
from cli.reviewer_agent import (
    build_review_packet,
    build_review_prompt,
    run_review,
    format_review_result,
)


def run_review_cmd(args) -> int:
    task_id = getattr(args, "task_id", None)
    stage = getattr(args, "stage", "build")
    backend = getattr(args, "backend", "file")
    model = getattr(args, "model", "claude-sonnet-4-6")
    worktrees_dir = Path(getattr(args, "worktrees_dir", ".sextant-worktrees")).resolve()
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces")).resolve()

    if not task_id:
        print("Usage: sextant review --task-id <id> [--stage build] [--backend file|claude]")
        print("")
        print("  Invoke a Reviewer to inspect a task's output.")
        print("")
        print("  Options:")
        print("    --stage    Review stage: spec|plan|build (default: build)")
        print("    --backend  Review backend: file|claude (default: file)")
        print("    --model    Model to use (default: claude-sonnet-4-6)")
        print("")
        print("  Active tasks:")
        from cli.state import list_active_tasks
        active = list_active_tasks(states_dir)
        for t in active:
            print(f"    {t.task_id}  [{t.state.value}]")
        return 1

    state = load_state(states_dir, task_id)
    wt = get_worktree_info(task_id, worktrees_dir)

    # Transition to reviewing
    state.transition_to(TaskState.REVIEWING, f"review started (backend: {backend})")
    save_state(states_dir, state)

    print(f"Review: {task_id} (stage: {stage}, backend: {backend})")
    print("")

    # Run automated review
    result = run_review(
        task_id=task_id,
        stage=stage,
        worktrees_dir=worktrees_dir,
        traces_dir=traces_dir,
        backend=backend,
        model=model,
    )

    print("")
    print(format_review_result(result))
    print("")

    # Update state based on verdict
    verdict = (result.verdict or "").lower()
    if verdict == "approved":
        state.transition_to(TaskState.APPROVED, "review approved")
        print("  Next: sextant merge --task-id", task_id)
    elif verdict == "approved-with-conditions":
        state.transition_to(TaskState.APPROVED, f"approved with {len(result.conditions)} conditions")
        print(f"  {len(result.conditions)} condition(s) to address")
        print("  Next: sextant merge --task-id", task_id, " (address conditions first)")
    elif verdict == "changes-requested":
        state.transition_to(TaskState.LOCAL_FAILED, "review requested changes")
        print("  Changes requested — return to execution")
        print("  Next: sextant execute --task-id", task_id)
    elif verdict == "rejected":
        state.transition_to(TaskState.FAILED, "review rejected")
        print("  Task rejected — requires replanning")
    else:
        # Pending — review not yet produced
        state.transition_to(TaskState.REVIEWING, "awaiting review completion")
        print("  Review pending — fill REVIEW.md and re-run:")
        print("    sextant review --task-id", task_id)

    save_state(states_dir, state)
    print("")
    print(format_state(state))

    return 0

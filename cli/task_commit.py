"""
Shared Worker-change commit logic for run.py and execute.py.

Both the DAG executor (run) and single-task executor (execute) need
the same semantics: verify → commit → transition to LOCAL_VERIFIED.
This module provides the single commit helper both call.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

from cli.worktree import SEXTANT_RUNTIME_FILES


def commit_worker_changes(worktree_path: Path, task_id: str) -> tuple[bool | None, str]:
    """Stage, filter, and commit Worker changes in the worktree.

    Uses git diff --cached --quiet to detect staged changes — no stderr
    parsing needed. Sextant runtime files are always excluded.

    Returns:
        (True,  detail)  — commit succeeded, Worker changes captured
        (False, detail)  — commit failed (git identity, hook, etc.)
        (None,  detail)  — no Worker changes staged (clean worktree, OK)
    """
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
        ).check_returncode()
    except subprocess.CalledProcessError as e:
        return False, f"git add failed: {e.stderr.strip() if e.stderr else 'unknown'}"

    # Unstage Sextant's own runtime files — never committed to branch
    for rf in SEXTANT_RUNTIME_FILES:
        subprocess.run(
            ["git", "reset", "--", rf],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

    # Check whether any real Worker changes are staged
    diff_proc = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if diff_proc.returncode == 0:
        # No staged changes — clean worktree (only runtime files were there)
        return None, "no worker changes to commit"
    if diff_proc.returncode != 1:
        # --quiet exits 1 when there ARE changes; anything else is an error
        return False, f"git diff --cached failed: {diff_proc.stderr.strip()}"

    # Worker changes detected — commit them
    commit_proc = subprocess.run(
        ["git", "commit", "-m", f"sextant: {task_id} — verified changes"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if commit_proc.returncode != 0:
        err = commit_proc.stderr.strip() or commit_proc.stdout.strip()
        return False, err or "commit failed"

    return True, "committed"

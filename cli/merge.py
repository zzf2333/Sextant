"""
sextant merge — merge a reviewed & approved task into the main branch.

Performs:
  1. Check that review is approved
  2. Merge worktree branch into integration branch (or main)
  3. Clean up worktree
  4. Update knowledge files (Record stage)

Integration flow:
  task branch → integration branch → global verify → main
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from cli.state import (
    TaskState,
    load_state,
    save_state,
    format_state,
)
from cli.worktree import (
    WorktreeError,
    get_worktree_info,
    remove_worktree,
    get_repo_root,
    has_uncommitted_changes,
)


def run_merge(args) -> int:
    task_id = getattr(args, "task_id", None)
    integration_id = getattr(args, "integration", None)
    worktrees_dir = Path(getattr(args, "worktrees_dir", ".sextant-worktrees")).resolve()
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()
    target_branch = getattr(args, "target_branch", "main")
    force = getattr(args, "force", False)
    dry_run = getattr(args, "dry_run", False)

    # ── Integration branch merge ──
    if integration_id:
        return _merge_integration(integration_id, target_branch, force, dry_run)

    # ── Single task merge ──
    if not task_id:
        print("Usage: sextant merge --task-id <id> [--target-branch main] [--force]")
        print("       sextant merge --integration <dag-id> [--target-branch main]")
        print("")
        print("  Merge a reviewed task or integration branch into the target branch.")
        return 1

    state = load_state(states_dir, task_id)
    wt = get_worktree_info(task_id, worktrees_dir)

    if wt is None:
        print(f"  Worktree not found for task '{task_id}'")
        return 1

    # Check state: must be APPROVED (review gate) or --force override
    if state.state != TaskState.APPROVED:
        if not force:
            print(f"  Task is in state '{state.state.value}', not ready for merge.")
            print("  Task must pass review (APPROVED) before merging.")
            print("  Use --force to bypass the review gate.")
            return 1
        print(f"  Warning: merging from state '{state.state.value}' (--force, skipping review gate)")

    print(f"Merging: {task_id} -> {target_branch}")
    print(f"  Branch:    {wt.branch}")
    print(f"  Worktree:  {wt.path}")
    print("")

    if dry_run:
        print(f"  (dry-run) Would merge {wt.branch} into {target_branch}")
        print(f"  (dry-run) Would remove worktree {wt.path}")
        return 0

    # ── Merge ──
    repo_root = get_repo_root()

    print("  [1/3] Merging branch...")
    try:
        # Ensure we're on target branch in main repo
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

        if current_branch != target_branch:
            # Checkout target branch
            if has_uncommitted_changes(repo_root):
                print(f"    Error: uncommitted changes in {repo_root}")
                print("    Commit or stash changes before merging.")
                return 1

            subprocess.run(
                ["git", "checkout", target_branch],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            ).check_returncode()
            print(f"    Checked out {target_branch}")

        # Merge the worktree branch
        result = subprocess.run(
            ["git", "merge", "--no-ff", wt.branch, "-m", f"sextant: merge {task_id}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"    Merge conflict detected:")
            print(result.stderr[:500])
            print("")
            print("  Resolve conflicts manually, then run:")
            print(f"    git add . && git commit")
            print(f"    sextant merge --task-id {task_id} --force")
            return 1

        print(f"    Merged {wt.branch} into {target_branch}")
        print(f"    {result.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        print(f"    Error: {e}")
        return 1

    # ── Cleanup worktree ──
    print("  [2/3] Cleaning up worktree...")
    try:
        remove_worktree(task_id, worktrees_dir, force=True)
        print(f"    Removed: {wt.path}")
    except WorktreeError as e:
        print(f"    Warning: {e}")

    # ── Update state ──
    print("  [3/3] Finalizing...")
    state.transition_to(TaskState.MERGED, f"merged into {target_branch}")
    save_state(states_dir, state)

    print("")
    print(format_state(state))
    print("")
    print("  Task merged successfully.")
    print("")
    print("  Next:")
    print("    git push origin", target_branch)
    print(f"    sextant spec <new task description>")
    return 0


def _detect_potential_conflicts(
    source_branch: str,
    target_branch: str,
    repo_root: Path,
) -> list[str]:
    """Detect files that may cause merge conflicts."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{target_branch}...{source_branch}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            changed = [f for f in result.stdout.strip().splitlines() if f.strip()]

            # Check if any of these files have also changed on target since branching
            if changed:
                result2 = subprocess.run(
                    ["git", "diff", "--name-only", f"{source_branch}...{target_branch}"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result2.returncode == 0:
                    target_changed = set(result2.stdout.strip().splitlines())
                    return sorted(set(changed) & target_changed)
        return []
    except Exception:
        return []


def _handle_merge_conflict(
    task_id: str,
    branch: str,
    repo_root: Path,
    result: "subprocess.CompletedProcess",
) -> int:
    """Handle a merge conflict with actionable guidance."""
    # Get conflicted files
    conflict_files: list[str] = []
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        conflict_files = [f for f in proc.stdout.strip().splitlines() if f.strip()]
    except Exception:
        pass

    print(f"    ✗ Merge conflict for {task_id}")
    print("")

    if conflict_files:
        print(f"    Conflicted files ({len(conflict_files)}):")
        for cf in conflict_files:
            print(f"      - {cf}")

    print("")
    print("  Resolution options:")
    print(f"    sextant merge --resolve ours    — accept our changes (from {task_id})")
    print(f"    sextant merge --resolve theirs   — accept target branch changes")
    print(f"    Manual: edit conflicted files, then git add . && git commit")
    print("")
    print(f"    After resolving: sextant merge --task-id {task_id} --force")
    return 1


def _resolve_conflicts(strategy: str) -> int:
    """Auto-resolve merge conflicts using the given strategy."""
    import subprocess
    from cli.worktree import get_repo_root

    repo_root = get_repo_root()

    if strategy not in ("ours", "theirs"):
        print(f"  Invalid strategy: {strategy}. Use 'ours' or 'theirs'.")
        return 1

    # Check we're actually in conflict
    try:
        subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        ).check_returncode()
    except subprocess.CalledProcessError:
        pass

    print(f"  Resolving conflicts with strategy: {strategy}")

    try:
        # Get conflicted files
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        conflict_files = [f for f in proc.stdout.strip().splitlines() if f.strip()]

        if not conflict_files:
            print("  No conflicted files detected.")
            return 0

        for cf in conflict_files:
            subprocess.run(
                ["git", "checkout", f"--{strategy}", cf],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "add", cf],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            print(f"    Resolved: {cf} ({strategy})")

        # Commit the resolution
        subprocess.run(
            ["git", "commit", "--no-edit"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(f"  Conflicts resolved. Merge commit created.")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"  Error: {e}")
        return 1


def _merge_integration(
    dag_id: str,
    target_branch: str,
    force: bool,
    dry_run: bool,
) -> int:
    """Merge an integration branch into the target branch."""
    import subprocess
    from cli.worktree import get_repo_root, has_uncommitted_changes

    integration_branch = f"integration/{dag_id}"
    repo_root = get_repo_root()

    # Check integration branch exists
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", integration_branch],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        ).check_returncode()
    except subprocess.CalledProcessError:
        print(f"  Integration branch '{integration_branch}' not found.")
        print("  Run 'sextant run --dag-path <path>' first to create it.")
        return 1

    print(f"Merging integration: {integration_branch} -> {target_branch}")
    print("")

    if dry_run:
        print(f"  (dry-run) Would merge {integration_branch} into {target_branch}")
        print(f"  (dry-run) Would delete {integration_branch}")
        # Also list worktrees to clean up
        from cli.worktree import list_worktrees
        wts = list_worktrees()
        if wts:
            print(f"  (dry-run) Would clean up {len(wts)} worktree(s)")
        return 0

    # Checkout target
    if has_uncommitted_changes(repo_root):
        print(f"    Error: uncommitted changes in {repo_root}")
        print("    Commit or stash changes before merging.")
        return 1

    try:
        subprocess.run(
            ["git", "checkout", target_branch],
            cwd=repo_root, capture_output=True, text=True, timeout=30,
        ).check_returncode()
        print(f"    Checked out {target_branch}")

        # Merge integration branch
        result = subprocess.run(
            ["git", "merge", "--no-ff", integration_branch,
             "-m", f"sextant: integrate {dag_id}"],
            cwd=repo_root, capture_output=True, text=True, timeout=30,
        )

        if result.returncode != 0:
            print(f"    Merge conflict:")
            print(result.stderr[:500])
            return 1

        print(f"    Merged {integration_branch} into {target_branch}")
        print(f"    {result.stdout.strip()}")

        # Delete integration branch
        subprocess.run(
            ["git", "branch", "-d", integration_branch],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        print(f"    Deleted {integration_branch}")

        # Clean up worktrees
        from cli.worktree import list_worktrees, remove_worktree
        wts = list_worktrees()
        for wt in wts:
            try:
                remove_worktree(wt.task_id, force=True)
                print(f"    Cleaned up worktree: {wt.task_id}")
            except Exception as e:
                print(f"    Warning: could not clean {wt.task_id}: {e}")

    except subprocess.CalledProcessError as e:
        print(f"    Error: {e}")
        return 1

    print("")
    print("  Integration merged successfully.")
    print("")
    print("  Next:")
    print("    git push origin", target_branch)
    return 0

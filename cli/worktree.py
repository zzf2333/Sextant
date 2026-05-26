"""
Git worktree management for Sextant v2.

Each task gets an isolated git worktree under .sextant-worktrees/<task_id>/.
The worktree is created from a base branch (default: main) on a feature branch
named sextant/task/<task_id>.

Operations:
  - create: git worktree add + checkout new branch
  - cleanup: git worktree remove + branch delete
  - list: list all sextant-managed worktrees
"""
from __future__ import annotations
import subprocess
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WorktreeInfo:
    task_id: str
    path: Path
    branch: str
    base_branch: str
    exists: bool


class WorktreeError(Exception):
    """Raised when a worktree operation fails."""
    pass


def _run_git(args: list[str], cwd: Optional[Path] = None, capture: bool = True) -> str:
    """Run a git command and return stdout. Raises WorktreeError on failure."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "unknown error"
            raise WorktreeError(f"git {' '.join(args)}: {stderr}")
        return result.stdout if capture else ""
    except subprocess.TimeoutExpired:
        raise WorktreeError(f"git {' '.join(args)}: timed out")
    except FileNotFoundError:
        raise WorktreeError("git command not found. Is git installed?")


def get_repo_root(cwd: Optional[Path] = None) -> Path:
    """Get the git repository root."""
    output = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(output.strip())


def get_current_branch(cwd: Optional[Path] = None) -> str:
    """Get the current branch name."""
    output = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return output.strip()


def has_uncommitted_changes(cwd: Optional[Path] = None) -> bool:
    """Check if the working tree has uncommitted changes."""
    output = _run_git(["status", "--porcelain"], cwd=cwd)
    return bool(output.strip())


def branch_exists(branch_name: str, cwd: Optional[Path] = None) -> bool:
    """Check if a git branch exists (local or remote)."""
    try:
        _run_git(["rev-parse", "--verify", branch_name], cwd=cwd)
        return True
    except WorktreeError:
        pass
    try:
        _run_git(["rev-parse", "--verify", f"origin/{branch_name}"], cwd=cwd)
        return True
    except WorktreeError:
        return False


def create_worktree(
    task_id: str,
    base_branch: str = "main",
    worktrees_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> WorktreeInfo:
    """Create a git worktree for a task.

    Args:
        task_id: Task identifier (used for branch name and directory)
        base_branch: Branch to create the worktree from (default: main)
        worktrees_dir: Parent directory for worktrees (default: .sextant-worktrees/)
        cwd: Working directory for git operations (default: cwd)

    Returns:
        WorktreeInfo with metadata about the created worktree

    Raises:
        WorktreeError: If worktree creation fails
    """
    repo_root = get_repo_root(cwd)
    if worktrees_dir is None:
        worktrees_dir = repo_root / ".sextant-worktrees"

    branch_name = f"sextant/task/{task_id}"
    worktree_path = worktrees_dir / task_id

    # Safety checks
    if worktree_path.exists():
        raise WorktreeError(
            f"Worktree already exists at {worktree_path}. "
            f"Run 'sextant cleanup {task_id}' first."
        )

    if has_uncommitted_changes(repo_root):
        raise WorktreeError(
            "Repository has uncommitted changes. "
            "git worktree requires a clean working tree.\n"
            "  Options:\n"
            "    1. Commit or stash your changes: git stash && sextant execute ...\n"
            "    2. Create from a clean ref: sextant execute --base-ref <commit-sha>\n"
            "       (uses a detached worktree from a specific commit, bypassing the clean check)"
        )

    # Create worktree with new branch
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    _run_git(
        ["worktree", "add", "-b", branch_name, str(worktree_path), base_branch],
        cwd=repo_root,
    )

    # Persist worktree metadata so list/get worktrees can recover base_branch
    meta_path = worktree_path / ".sextant-worktree-meta.json"
    import json
    meta_path.write_text(json.dumps({
        "task_id": task_id,
        "base_branch": base_branch,
    }), encoding="utf-8")

    return WorktreeInfo(
        task_id=task_id,
        path=worktree_path,
        branch=branch_name,
        base_branch=base_branch,
        exists=True,
    )


def remove_worktree(
    task_id: str,
    worktrees_dir: Optional[Path] = None,
    force: bool = False,
    cwd: Optional[Path] = None,
) -> None:
    """Remove a task's git worktree and optionally its branch.

    Args:
        task_id: Task identifier
        worktrees_dir: Parent directory for worktrees
        force: Force removal even with uncommitted changes
        cwd: Working directory for git operations

    Raises:
        WorktreeError: If removal fails
    """
    repo_root = get_repo_root(cwd)
    if worktrees_dir is None:
        worktrees_dir = repo_root / ".sextant-worktrees"

    worktree_path = worktrees_dir / task_id
    branch_name = f"sextant/task/{task_id}"

    if not worktree_path.exists():
        raise WorktreeError(f"Worktree not found: {worktree_path}")

    # Remove worktree (detach from git first)
    force_flag = ["--force"] if force else []
    _run_git(
        ["worktree", "remove"] + force_flag + [str(worktree_path)],
        cwd=repo_root,
    )

    # Clean up branch
    try:
        _run_git(["branch", "-D", branch_name], cwd=repo_root)
    except WorktreeError:
        # Branch may already be merged/deleted — ignore
        pass


def list_worktrees(
    worktrees_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> list[WorktreeInfo]:
    """List all sextant-managed worktrees.

    Args:
        worktrees_dir: Parent directory for worktrees
        cwd: Working directory for git operations

    Returns:
        List of WorktreeInfo (only those managed by Sextant)
    """
    try:
        repo_root = get_repo_root(cwd)
    except WorktreeError:
        return []

    if worktrees_dir is None:
        worktrees_dir = repo_root / ".sextant-worktrees"

    if not worktrees_dir.exists():
        return []

    worktrees: list[WorktreeInfo] = []
    for d in sorted(worktrees_dir.iterdir()):
        if not d.is_dir():
            continue
        task_id = d.name
        branch_name = f"sextant/task/{task_id}"

        # Read persisted base_branch from metadata file
        base_branch = "main"  # fallback
        meta_file = d / ".sextant-worktree-meta.json"
        if meta_file.exists():
            try:
                import json
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                base_branch = meta.get("base_branch", "main")
            except (json.JSONDecodeError, OSError):
                pass

        wt = WorktreeInfo(
            task_id=task_id,
            path=d,
            branch=branch_name,
            base_branch=base_branch,
            exists=True,
        )
        worktrees.append(wt)

    return worktrees


def get_worktree_info(
    task_id: str,
    worktrees_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> Optional[WorktreeInfo]:
    """Get info for a specific task's worktree."""
    for wt in list_worktrees(worktrees_dir, cwd):
        if wt.task_id == task_id:
            return wt
    return None


def worktree_has_changes(
    task_id: str,
    worktrees_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> bool:
    """Check if a worktree has uncommitted changes."""
    wt = get_worktree_info(task_id, worktrees_dir, cwd)
    if wt is None or not wt.exists:
        return False
    return has_uncommitted_changes(wt.path)

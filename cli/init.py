"""
sextant init — initialize Sextant v2 in a project.

Creates:
  - .sextant/ directory with knowledge files
  - .sextant-worktrees/ directory (gitignored)
  - .sextant/states/ directory for task state tracking
"""
from __future__ import annotations
import sys
from pathlib import Path


def run_init(args) -> int:
    project_root = Path(getattr(args, "project_root", ".")).resolve()
    force = getattr(args, "force", False)

    sextant_dir = project_root / ".sextant"
    worktrees_dir = project_root / ".sextant-worktrees"
    states_dir = project_root / ".sextant" / "states"
    traces_dir = project_root / ".sextant" / "traces"

    dirs_to_create = [sextant_dir, worktrees_dir, states_dir, traces_dir]

    # Check .gitignore
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        missing = []
        for pattern in [".sextant-worktrees/", ".sextant/traces/"]:
            if pattern not in content:
                missing.append(pattern)
        if missing:
            if force:
                with gitignore_path.open("a") as f:
                    f.write("\n# Sextant\n")
                    for p in missing:
                        f.write(f"{p}\n")
                print(f"  Added to .gitignore: {', '.join(missing)}")
            else:
                print(f"  Warning: add to .gitignore: {', '.join(missing)}")

    # Create directories
    created = []
    for d in dirs_to_create:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(str(d.relative_to(project_root)))

    if created:
        print(f"  Created: {', '.join(created)}")
    else:
        print("  Directories already exist")

    # Check if git repo
    has_git = (project_root / ".git").exists()
    if not has_git:
        print("  Warning: not a git repository. Worktree features require git.")

    print("")
    print("  Sextant v2 initialized.")
    print(f"  Project root: {project_root}")
    print("")
    print("  Next steps:")
    print("    sextant spec    — define a task specification")
    print("    sextant status  — view active tasks")
    return 0

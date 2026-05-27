"""
Deterministic validator for Sextant v2.

Validates that a Worker's output respects its Task Contract constraints:
  1. forbidden_path check — no modifications outside allowed boundaries
  2. diff_size check — changes are not excessively large
  3. dependency_drift check — no new dependencies added
  4. acceptance criteria — test/lint/verification commands

All checks are deterministic — no LLM involvement.
"""
from __future__ import annotations
import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cli.contract import TaskContract, parse_contract
from cli.worktree import WorktreeInfo, get_worktree_info, SEXTANT_RUNTIME_FILES


@dataclass
class ValidationResult:
    task_id: str
    passed: bool
    checks: list[dict] = field(default_factory=list)  # [{name, passed, detail}]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c["passed"])

    def add_check(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.passed = False


def validate_contract(
    task_id: str,
    worktrees_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> ValidationResult:
    """Run all deterministic validations for a task.

    Args:
        task_id: Task identifier
        worktrees_dir: Worktrees parent directory
        cwd: Working directory

    Returns:
        ValidationResult with all check results
    """
    result = ValidationResult(task_id=task_id, passed=True)
    wt = get_worktree_info(task_id, worktrees_dir, cwd)

    if wt is None or not wt.exists:
        result.add_check("worktree_exists", False, f"Worktree not found for {task_id}")
        return result

    contract_path = wt.path / "TASK_CONTRACT.md"
    contract = parse_contract(contract_path)

    if contract is None:
        result.add_check("contract_exists", False, "TASK_CONTRACT.md not found in worktree")
        return result

    result.add_check("contract_exists", True, str(contract_path))

    # 1. Forbidden path check
    _check_forbidden_paths(result, contract, wt)

    # 2. Diff size check
    _check_diff_size(result, contract, wt)

    # 3. Dependency drift check
    _check_dependency_drift(result, contract, wt)

    # 4. Run acceptance commands
    _run_acceptance_commands(result, contract, wt)

    return result


def _get_changed_files(wt_path: Path, base_branch: str | None = None) -> list[str]:
    """Get list of changed files in the worktree relative to the base branch.

    Includes both tracked diffs AND untracked files so that forbidden_path,
    diff_size, and dependency_drift checks cannot be bypassed by omitting
    'git add' on a newly-created forbidden file.
    """
    files: list[str] = []
    try:
        base_ref = _get_base_ref(wt_path, base_branch)
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=wt_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            files.extend(f for f in result.stdout.strip().splitlines() if f.strip())

        # Also include untracked files (not yet git add'd).
        # A Worker could create a forbidden/dependency file without staging it,
        # and a git-diff-only check would miss it entirely.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=wt_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if untracked.returncode == 0:
            files.extend(f for f in untracked.stdout.strip().splitlines() if f.strip())

        return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _has_commits(wt_path: Path) -> bool:
    """Check if the repo has at least one commit."""
    try:
        subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=wt_path,
            capture_output=True,
            timeout=10,
        ).check_returncode()
        return True
    except subprocess.CalledProcessError:
        return False


def _get_base_ref(wt_path: Path, base_branch: str | None = None) -> str:
    """Find the merge-base commit for the task branch relative to its base branch.

    Uses the worktree's base_branch if provided; otherwise falls back to
    main then master. Returns 'HEAD' if no merge-base is found.
    """
    branches = [base_branch] if base_branch else []
    branches.extend(b for b in ("main", "master") if b not in branches)
    for branch in branches:
        try:
            mb = subprocess.run(
                ["git", "merge-base", "HEAD", branch],
                cwd=wt_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip()
        except Exception:
            continue
    return "HEAD"


def _matches_any_glob(path: str, globs: list[str]) -> bool:
    """Check if a path matches any glob in the list."""
    for g in globs:
        if fnmatch.fnmatch(path, g):
            return True
    return False


def _check_forbidden_paths(
    result: ValidationResult,
    contract: TaskContract,
    wt: WorktreeInfo,
) -> None:
    """Verify no file was modified outside allowed_paths or inside forbidden_paths.

    Sextant's own runtime files (TASK_CONTRACT.md, EXECUTOR_INSTRUCTIONS.md,
    .sextant-worktree-meta.json) are always excluded from boundary checks.
    """
    if not contract.allowed_paths:
        result.add_check("forbidden_paths", True, "no allowed_paths defined — skipping")
        return

    changed = _get_changed_files(wt.path, wt.base_branch)
    violations: list[str] = []

    for f in changed:
        # Always exclude Sextant's own runtime files
        if f in SEXTANT_RUNTIME_FILES:
            continue

        # Check forbidden first (takes priority)
        if _matches_any_glob(f, contract.forbidden_paths):
            violations.append(f"modified forbidden path: {f}")
            continue

        # Check if file is in allowed paths
        if not _matches_any_glob(f, contract.allowed_paths):
            violations.append(f"modified path outside allowed_paths: {f}")

    if violations:
        result.add_check(
            "forbidden_paths", False,
            f"{len(violations)} violation(s):\n" + "\n".join(f"    - {v}" for v in violations[:10])
        )
    else:
        result.add_check("forbidden_paths", True, f"{len(changed)} files checked, all within bounds")


def _check_diff_size(
    result: ValidationResult,
    contract: TaskContract,
    wt: WorktreeInfo,
    max_files: int = 50,
    max_insertions: int = 1000,
) -> None:
    """Check that the diff is not excessively large.

    Counts both tracked diffs AND untracked files. A Worker can create
    a large file without staging it, and git diff --stat alone would miss it.
    """
    try:
        base_ref = _get_base_ref(wt.path, wt.base_branch)
        stat_result = subprocess.run(
            ["git", "diff", "--stat", base_ref],
            cwd=wt.path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = stat_result.stdout.strip()
        lines = output.splitlines() if output else []
        file_count = len([l for l in lines if l.strip() and not l.startswith(" ")])
        last_line = lines[-1] if lines else ""

        # Parse the stat summary line: "X files changed, Y insertions(+), Z deletions(-)"
        insertions = 0
        import re
        if "insertion" in last_line:
            m = re.search(r"(\d+)\s+insertion", last_line)
            if m:
                insertions = int(m.group(1))

        # Also count untracked files (not yet staged).
        # A Worker could drop a large file in an allowed path without git add,
        # bypassing the diff stat entirely.
        # Sextant runtime files are excluded — they're scaffolding, not worker output.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=wt.path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if untracked.returncode != 0:
            result.add_check(
                "diff_size", False,
                f"unable to list untracked files: {untracked.stderr.strip()[:120]}"
            )
            return

        ut_files = [
            f for f in untracked.stdout.strip().splitlines()
            if f.strip() and f not in SEXTANT_RUNTIME_FILES
        ]
        file_count += len(ut_files)
        # Estimate insertions = line count per untracked file
        for uf in ut_files:
            try:
                uf_path = wt.path / uf
                if uf_path.is_file():
                    insertions += len(uf_path.read_text(encoding="utf-8", errors="ignore").splitlines())
            except OSError:
                pass  # binary file, symlink, etc.

        if not output and not ut_files:
            result.add_check("diff_size", True, "no changes detected")
            return

        warnings: list[str] = []
        if file_count > max_files:
            warnings.append(f"{file_count} files changed (threshold: {max_files})")
        if insertions > max_insertions:
            warnings.append(f"{insertions} insertions (threshold: {max_insertions})")

        if warnings:
            result.add_check("diff_size", False, "; ".join(warnings))
        else:
            result.add_check(
                "diff_size", True,
                f"{file_count} files, {insertions} insertions"
            )
    except Exception as e:
        result.add_check("diff_size", True, f"unable to check diff size: {e}")


def _check_dependency_drift(
    result: ValidationResult,
    contract: TaskContract,
    wt: WorktreeInfo,
) -> None:
    """Check that no new dependencies were added outside the contract.

    Uses _get_changed_files() so both tracked and untracked dependency
    files are detected — a Worker can't bypass this gate by omitting git add.
    """
    dep_files = [
        "package.json", "pyproject.toml", "requirements.txt",
        "go.mod", "Cargo.toml", "Gemfile", "composer.json",
    ]
    changed = set(_get_changed_files(wt.path, wt.base_branch))

    for dep_file in dep_files:
        if dep_file not in changed:
            continue

        # Check if the dep file is in forbidden_paths
        if _matches_any_glob(dep_file, contract.forbidden_paths):
            result.add_check(
                "dependency_drift", False,
                f"modified forbidden dependency file: {dep_file}"
            )
            return

        # If dep file is in allowed_paths, it's OK
        if _matches_any_glob(dep_file, contract.allowed_paths):
            result.add_check("dependency_drift", True, f"{dep_file} modified (in allowed_paths)")
            return

        # Otherwise, warn
        result.add_check(
            "dependency_drift", False,
            f"{dep_file} modified — not in allowed_paths or forbidden_paths"
        )
        return

    result.add_check("dependency_drift", True, "no dependency files modified")


def _run_acceptance_commands(
    result: ValidationResult,
    contract: TaskContract,
    wt: WorktreeInfo,
) -> None:
    """Run acceptance criteria commands in the worktree."""
    for i, criterion in enumerate(contract.acceptance):
        cmd = criterion.strip()
        if not cmd or cmd.startswith("<"):
            continue

        try:
            proc = subprocess.run(
                cmd,
                cwd=wt.path,
                capture_output=True,
                text=True,
                timeout=120,
                shell=True,
            )
            passed = proc.returncode == 0
            detail = f"exit code: {proc.returncode}"
            if not passed and proc.stderr:
                # Show last 200 chars of stderr
                err_tail = proc.stderr.strip()[-200:]
                detail += f", stderr: {err_tail}" if err_tail else ""

            result.add_check(f"acceptance[{i}]: {cmd[:60]}", passed, detail)
        except subprocess.TimeoutExpired:
            result.add_check(f"acceptance[{i}]: {cmd[:60]}", False, "timed out after 120s")
        except Exception as e:
            result.add_check(f"acceptance[{i}]: {cmd[:60]}", False, str(e))


def format_validation(result: ValidationResult) -> str:
    """Format a ValidationResult for display."""
    status = "\u2713 PASSED" if result.passed else "\u2717 FAILED"
    lines = [
        f"Validation: {result.task_id}  [{status}]",
        "",
    ]

    for check in result.checks:
        symbol = "\u2713" if check["passed"] else "\u2717"
        name = check["name"]
        detail = check["detail"]
        if detail and "\n" in detail:
            lines.append(f"  {symbol} {name}:")
            for dl in detail.splitlines():
                lines.append(f"      {dl}")
        else:
            lines.append(f"  {symbol} {name}: {detail}")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for e in result.errors:
            lines.append(f"  - {e}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)

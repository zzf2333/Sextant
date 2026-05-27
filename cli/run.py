"""
sextant run — parallel execution entry point (Phase 2 MVP).

Parses a task DAG, determines which tasks can run in parallel,
and executes them via git worktrees + Reasonix Workers.

Flow:
  1. Parse + validate DAG
  2. Execute foundation tasks sequentially
  3. Execute parallel implementation tasks concurrently (up to --parallel N)
  4. Execute integration tasks sequentially
  5. Create integration branch, merge all worktrees
  6. Run global verify
  7. Report results
"""
from __future__ import annotations
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from cli.scheduler import TaskDAG, TaskNode, load_dag, TaskDAGError
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
    list_worktrees,
    get_repo_root,
    has_uncommitted_changes,
    SEXTANT_RUNTIME_FILES,
)
from cli.validator import validate_contract, format_validation, ValidationResult


# ── Execution result types ────────────────────────────────────────────

@dataclass
class TaskResult:
    task_id: str
    success: bool
    worktree: Optional[WorktreeInfo] = None
    verify_result: Optional[ValidationResult] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class DAGResult:
    dag_id: str
    results: list[TaskResult] = field(default_factory=list)
    integration_branch: Optional[str] = None
    global_verify: Optional[ValidationResult] = None
    total_duration_seconds: float = 0.0

    @property
    def all_passed(self) -> bool:
        tasks_ok = all(r.success for r in self.results)
        global_ok = self.global_verify.passed if self.global_verify else True
        return tasks_ok and global_ok

    @property
    def failed_tasks(self) -> list[str]:
        return [r.task_id for r in self.results if not r.success]


# ── DAG Executor ──────────────────────────────────────────────────────

class DAGExecutor:
    """Executes a TaskDAG with worktree isolation and parallel scheduling."""

    def __init__(
        self,
        dag: TaskDAG,
        worktrees_dir: Path,
        traces_dir: Path,
        states_dir: Path,
        base_branch: str = "main",
        max_workers: int = 4,
        runtime: str = "reasonix",
        dry_run: bool = False,
        on_progress: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.dag = dag
        self.worktrees_dir = worktrees_dir
        self.traces_dir = traces_dir
        self.states_dir = states_dir
        self.base_branch = base_branch
        self.max_workers = max_workers
        self.runtime = runtime
        self.dry_run = dry_run
        self.on_progress = on_progress or (lambda tid, status, msg: None)

    def execute(self) -> DAGResult:
        """Execute the full DAG and return results."""
        start_time = time.time()
        result = DAGResult(dag_id=self.dag.dag_id)

        # Validate DAG
        errors = self.dag.validate()
        if errors:
            for e in errors:
                print(f"  DAG validation error: {e}")
            return result

        completed: set[str] = set()

        # Phase 1: Foundation tasks (sequential)
        foundation = [t for t in self.dag.tasks if t.task_type == "foundation"]
        print(f"\n  Phase 1: Foundation tasks ({len(foundation)})")
        for task in foundation:
            if task.task_id in completed:
                continue
            tr = self._execute_single_task(task)
            result.results.append(tr)
            if tr.success:
                completed.add(task.task_id)
                task.state = "completed"
            else:
                print(f"    Foundation task '{task.task_id}' failed — aborting DAG")
                result.total_duration_seconds = time.time() - start_time
                return result

        # Phase 2: Parallel implementation tasks
        implementation = [t for t in self.dag.tasks if t.task_type == "implementation"]
        if implementation:
            print(f"\n  Phase 2: Implementation tasks ({len(implementation)}, parallelism={self.max_workers})")
            result.results.extend(
                self._execute_parallel(implementation, completed)
            )
            for tr in result.results:
                if tr.success and tr.task_id not in completed:
                    completed.add(tr.task_id)

        # Check for failures before proceeding
        failed = result.failed_tasks
        if failed:
            print(f"\n  {len(failed)} task(s) failed: {', '.join(failed)}")
            print("  Aborting — integration phase requires all tasks to pass")
            result.total_duration_seconds = time.time() - start_time
            return result

        # Phase 3: Integration tasks (sequential)
        integration = [t for t in self.dag.tasks if t.task_type == "integration"]
        if integration:
            print(f"\n  Phase 3: Integration tasks ({len(integration)})")
            for task in integration:
                if task.task_id in completed:
                    continue
                tr = self._execute_single_task(task)
                result.results.append(tr)
                if tr.success:
                    completed.add(task.task_id)
                else:
                    print(f"    Integration task '{task.task_id}' failed")
                    result.total_duration_seconds = time.time() - start_time
                    return result

        # Phase 4: Create integration branch and merge
        if result.all_passed and self.dag.tasks:
            print(f"\n  Phase 4: Integration branch")
            if not self.dry_run:
                integration_ok = self._create_integration_branch(result)
                if integration_ok:
                    print(f"    All worktrees merged into integration/{self.dag.dag_id}")
                    # Run global verify
                    result.global_verify = self._run_global_verify(result)
                else:
                    print("    \u2717 Integration branch creation failed")
                    result.global_verify = ValidationResult(
                        task_id=f"integration/{self.dag.dag_id}",
                        passed=False,
                        errors=["Integration branch creation failed — check for uncommitted changes or merge conflicts"],
                    )
            else:
                print(f"    (dry-run) Would create integration/{self.dag.dag_id}")

        result.total_duration_seconds = time.time() - start_time

        # Persist DAG gate status for merge gate enforcement
        self._save_gate_status(result)

        return result

    def _save_gate_status(self, result: DAGResult) -> None:
        """Save DAG result as gate status for merge enforcement."""
        import json
        gate_path = self.states_dir / f"dag-{self.dag.dag_id}.json"
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_data = {
            "dag_id": self.dag.dag_id,
            "all_passed": result.all_passed,
            "global_verify_passed": result.global_verify.passed if result.global_verify else False,
            "integration_branch": result.integration_branch,
            "total_duration_seconds": result.total_duration_seconds,
            "tasks": [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "error": r.error,
                }
                for r in result.results
            ],
        }
        gate_path.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")

    @staticmethod
    def load_gate_status(dag_id: str, states_dir: Path) -> dict | None:
        """Load persisted gate status for a DAG, if it exists."""
        import json
        gate_path = states_dir / f"dag-{dag_id}.json"
        if not gate_path.exists():
            return None
        try:
            return json.loads(gate_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _execute_single_task(self, task: TaskNode) -> TaskResult:
        """Execute a single task in its own worktree."""
        self.on_progress(task.task_id, "starting", f"{task.task_type}")
        start = time.time()

        if self.dry_run:
            print(f"    (dry-run) {task.task_id}: would execute in worktree")
            return TaskResult(
                task_id=task.task_id,
                success=True,
                duration_seconds=0,
            )

        try:
            # Create worktree
            self.on_progress(task.task_id, "worktree", "creating worktree")
            wt = create_worktree(task.task_id, self.base_branch, self.worktrees_dir)

            # Load contract
            contract_path = self.traces_dir / task.task_id / "TASK_CONTRACT.md"
            contract = parse_contract(contract_path)
            if contract is None:
                remove_worktree(task.task_id, self.worktrees_dir, force=True)
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Contract not found: {contract_path}",
                    duration_seconds=time.time() - start,
                )

            # Deploy contract to worktree
            (wt.path / "TASK_CONTRACT.md").write_text(
                contract.to_markdown(), encoding="utf-8"
            )

            # Deploy executor instructions
            self._write_executor_instructions(task.task_id, contract, wt)

            # Update state
            state = load_state(self.states_dir, task.task_id)
            state.worktree_path = str(wt.path)
            state.transition_to(TaskState.WORKTREE_CREATED, "worktree created")
            state.transition_to(TaskState.EXECUTING, f"execution started with {self.runtime}")
            save_state(self.states_dir, state)

            self.on_progress(task.task_id, "executing", self.runtime)
            print(f"    {task.task_id}: worktree ready at {wt.path}")
            print(f"    {task.task_id}: Worker should read TASK_CONTRACT.md + EXECUTOR_INSTRUCTIONS.md")

            # For MVP: execution is manual (Worker reads instructions)
            # In production: spawn Reasonix Worker subprocess here

            # Run local verify
            self.on_progress(task.task_id, "verifying", "local verify")
            state.transition_to(TaskState.LOCAL_VERIFYING, "local verify")
            save_state(self.states_dir, state)

            verify_result = validate_contract(task.task_id, self.worktrees_dir)
            duration = time.time() - start

            if verify_result.passed:
                # Commit MUST succeed before we transition to LOCAL_VERIFIED.
                # If commit fails, the integration merge will be empty —
                # local verify is void.
                committed = self._commit_worktree_changes(wt, task.task_id)
                if committed is False:
                    # Real commit failure: no git identity, hook failure, etc.
                    state.error_count += 1
                    state.last_error = "commit failed — changes not captured"
                    state.transition_to(TaskState.LOCAL_FAILED, "commit failed")
                    self.on_progress(task.task_id, "failed", "commit failed")
                    print(f"    {task.task_id}: \u2717 commit failed — local verify is void")
                    save_state(self.states_dir, state)
                    return TaskResult(
                        task_id=task.task_id,
                        success=False,
                        worktree=wt,
                        verify_result=verify_result,
                        error="commit failed — configure git identity and re-run",
                        duration_seconds=duration,
                    )

                # commit succeeded (True) or clean worktree (None) — either is fine
                state.transition_to(TaskState.LOCAL_VERIFIED, "local verify passed")
                self.on_progress(task.task_id, "passed", f"verified in {duration:.1f}s")
                print(f"    {task.task_id}: \u2713 local verify passed ({duration:.1f}s)")
            else:
                state.error_count += 1
                state.last_error = f"{verify_result.error_count} check(s) failed"
                state.transition_to(TaskState.LOCAL_FAILED, "local verify failed")
                self.on_progress(task.task_id, "failed", f"{verify_result.error_count} checks failed")
                print(f"    {task.task_id}: \u2717 local verify failed")
                print(format_validation(verify_result))

            save_state(self.states_dir, state)

            return TaskResult(
                task_id=task.task_id,
                success=verify_result.passed,
                worktree=wt,
                verify_result=verify_result,
                duration_seconds=duration,
            )

        except WorktreeError as e:
            duration = time.time() - start
            self.on_progress(task.task_id, "failed", str(e))
            print(f"    {task.task_id}: \u2717 {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start
            self.on_progress(task.task_id, "failed", str(e))
            print(f"    {task.task_id}: \u2717 unexpected error: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _execute_parallel(
        self,
        tasks: list[TaskNode],
        completed: set[str],
    ) -> list[TaskResult]:
        """Execute multiple implementation tasks respecting parallelizable flag.

        Non-parallelizable tasks run sequentially (one at a time).
        Parallelizable tasks run concurrently in waves (respecting dependencies).
        This matches the semantics of scheduler.get_parallel_groups().
        """
        results: list[TaskResult] = []
        remaining = list(tasks)

        while remaining:
            ready = [t for t in remaining if all(d in completed for d in t.depends_on)]
            if not ready:
                # No progress possible — unresolved dependencies
                unresolved = [t for t in remaining if not all(d in completed for d in t.depends_on)]
                for t in unresolved:
                    missing = [d for d in t.depends_on if d not in completed]
                    results.append(TaskResult(
                        task_id=t.task_id,
                        success=False,
                        error=f"unresolved dependencies: {missing}",
                    ))
                break

            # Split: non-parallelizable tasks run sequentially first
            sequential = [t for t in ready if not t.parallelizable]
            parallelizable = [t for t in ready if t.parallelizable]

            # Execute non-parallelizable tasks one at a time
            for task in sequential:
                print(f"      Sequential: {task.task_id}")
                tr = self._execute_single_task(task)
                results.append(tr)
                if tr.success:
                    completed.add(task.task_id)

            # Execute parallelizable tasks concurrently
            if parallelizable:
                if len(parallelizable) > 1:
                    print(f"      Parallel ({len(parallelizable)} tasks, workers={self.max_workers})")
                else:
                    print(f"      Parallel: {parallelizable[0].task_id}")

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_map = {
                        executor.submit(self._execute_single_task, task): task
                        for task in parallelizable
                    }
                    for future in as_completed(future_map):
                        tr = future.result()
                        results.append(tr)
                        if tr.success:
                            completed.add(tr.task_id)

            # Remove all tasks from this wave from remaining
            remaining = [t for t in remaining if t not in ready]

        return results

    def _commit_worktree_changes(self, wt: WorktreeInfo, task_id: str) -> bool | None:
        """Stage and commit Worker changes to the task branch.

        Uses git diff --cached --quiet to detect staged changes before
        committing — no stderr parsing needed for "nothing to commit".

        Returns:
            True  — commit succeeded (worker changes captured)
            False — commit failed (git identity, hook, etc.) — task MUST fail
            None  — no staged changes after filtering (clean worktree, OK)
        """
        import subprocess

        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=wt.path, capture_output=True, text=True, timeout=30,
            ).check_returncode()

            # Unstage Sextant's own runtime files — never committed to branch
            for rf in SEXTANT_RUNTIME_FILES:
                subprocess.run(
                    ["git", "reset", "--", rf],
                    cwd=wt.path, capture_output=True, text=True, timeout=10,
                )

            # Check whether any real worker changes are staged
            diff_proc = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=wt.path, capture_output=True, text=True, timeout=10,
            )
            if diff_proc.returncode == 0:
                # No staged changes — clean worktree (only runtime files were there)
                print(f"    {task_id}: no worker changes to commit (worktree clean)")
                return None
            if diff_proc.returncode != 1:
                # --quiet exits 1 when there ARE changes; anything else is an error
                print(f"    {task_id}: git diff --cached failed (exit {diff_proc.returncode})")
                return False

            # Worker changes detected — commit them
            commit_proc = subprocess.run(
                ["git", "commit", "-m", f"sextant: {task_id} — verified changes"],
                cwd=wt.path, capture_output=True, text=True, timeout=30,
            )
            if commit_proc.returncode != 0:
                print(f"    {task_id}: COMMIT FAILED — {commit_proc.stderr.strip()[:300]}")
                return False

            print(f"    {task_id}: committed changes to {wt.branch}")
            return True

        except subprocess.CalledProcessError:
            print(f"    Warning: git add failed for {task_id}")
            return False

    def _write_executor_instructions(
        self,
        task_id: str,
        contract: TaskContract,
        wt: WorktreeInfo,
    ) -> None:
        """Write EXECUTOR_INSTRUCTIONS.md in the worktree."""
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

## DAG Context
DAG: {self.dag.dag_id}
Type: {contract.task_type}
""", encoding="utf-8")

    def _create_integration_branch(self, result: DAGResult) -> bool:
        """Create integration branch and merge all worktree branches into it."""
        import subprocess

        integration_branch = f"integration/{self.dag.dag_id}"
        repo_root = get_repo_root()
        result.integration_branch = integration_branch

        try:
            # Checkout base branch
            if has_uncommitted_changes(repo_root):
                print("    Warning: uncommitted changes in main repo — skipping integration")
                return False

            subprocess.run(
                ["git", "checkout", self.base_branch],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
            ).check_returncode()

            # Create integration branch from base
            try:
                subprocess.run(
                    ["git", "branch", "-D", integration_branch],
                    cwd=repo_root, capture_output=True, text=True, timeout=10,
                )
            except subprocess.CalledProcessError:
                pass  # branch doesn't exist yet

            subprocess.run(
                ["git", "checkout", "-b", integration_branch],
                cwd=repo_root, capture_output=True, text=True, timeout=30,
            ).check_returncode()

            # Merge each worktree branch
            for tr in result.results:
                if not tr.success:
                    continue
                branch_name = f"sextant/task/{tr.task_id}"
                try:
                    merge_result = subprocess.run(
                        ["git", "merge", "--no-ff", branch_name,
                         "-m", f"sextant: integrate {tr.task_id}"],
                        cwd=repo_root, capture_output=True, text=True, timeout=30,
                    )
                    if merge_result.returncode != 0:
                        print(f"    Merge conflict for {tr.task_id}:")
                        print(merge_result.stderr[:300])
                        return False
                    print(f"    Merged: {branch_name}")
                except subprocess.CalledProcessError as e:
                    print(f"    Failed to merge {branch_name}: {e}")
                    return False

            return True

        except Exception as e:
            print(f"    Integration error: {e}")
            return False

    def _run_global_verify(self, result: DAGResult) -> Optional[ValidationResult]:
        """Run global verification on the integration branch."""
        import subprocess

        repo_root = get_repo_root()
        print(f"\n    Running global verify on integration/{self.dag.dag_id}")

        try:
            # Run tests from integration branch
            # Detect test commands
            test_cmds = _detect_test_commands(repo_root)

            all_checks: list[dict] = []
            all_passed = True

            for cmd in test_cmds:
                proc = subprocess.run(
                    cmd, cwd=repo_root, capture_output=True,
                    text=True, timeout=120, shell=True,
                )
                passed = proc.returncode == 0
                detail = f"exit {proc.returncode}"
                if not passed and proc.stderr:
                    detail += f" | {proc.stderr.strip()[-100:]}"
                all_checks.append({"name": cmd, "passed": passed, "detail": detail})
                if not passed:
                    all_passed = False
                print(f"      {'\u2713' if passed else '\u2717'} {cmd}")

            vr = ValidationResult(
                task_id=f"integration/{self.dag.dag_id}",
                passed=all_passed,
                checks=all_checks,
            )
            return vr

        except Exception as e:
            print(f"    Global verify error: {e}")
            return ValidationResult(
                task_id=f"integration/{self.dag.dag_id}",
                passed=False,
                errors=[str(e)],
            )


def _detect_test_commands(repo_root: Path) -> list[str]:
    """Detect test commands from common project files."""
    cmds: list[str] = []

    # package.json
    pkg_json = repo_root / "package.json"
    if pkg_json.exists():
        cmds.append("npm test 2>&1")

    # pyproject.toml / setup.py
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        cmds.append("python3 -m pytest 2>&1")

    # Makefile
    makefile = repo_root / "Makefile"
    if makefile.exists():
        cmds.append("make test 2>&1")

    # go.mod
    if (repo_root / "go.mod").exists():
        cmds.append("go test ./... 2>&1")

    # Cargo.toml
    if (repo_root / "Cargo.toml").exists():
        cmds.append("cargo test 2>&1")

    if not cmds:
        cmds.append("echo '(no test commands detected)'")

    return cmds


# ── Display helpers ───────────────────────────────────────────────────

def _format_dag_summary(dag: TaskDAG) -> str:
    """Format a DAG summary for display."""
    foundation = [t for t in dag.tasks if t.task_type == "foundation"]
    implementation = [t for t in dag.tasks if t.task_type == "implementation"]
    integration = [t for t in dag.tasks if t.task_type == "integration"]

    lines = [
        f"DAG: {dag.dag_id}",
        f"Tasks: {len(dag.tasks)} ({len(foundation)} foundation, {len(implementation)} implementation, {len(integration)} integration)",
        "",
    ]

    if foundation:
        lines.append("  Foundation (sequential):")
        for t in foundation:
            deps = f" → [{', '.join(t.depends_on)}]" if t.depends_on else ""
            lines.append(f"    {t.task_id}{deps}")

    if implementation:
        lines.append("  Implementation:")
        for t in implementation:
            deps = f" → [{', '.join(t.depends_on)}]" if t.depends_on else ""
            par = "  [parallel]" if t.parallelizable else ""
            lines.append(f"    {t.task_id}{deps}{par}")

    if integration:
        lines.append("  Integration (sequential):")
        for t in integration:
            deps = f" → [{', '.join(t.depends_on)}]" if t.depends_on else ""
            lines.append(f"    {t.task_id}{deps}")

    return "\n".join(lines)


def _format_results_summary(result: DAGResult) -> str:
    """Format execution results for display."""
    passed = sum(1 for r in result.results if r.success)
    failed = sum(1 for r in result.results if not r.success)
    total = len(result.results)

    lines = [
        "",
        "=" * 60,
        f"  DAG Execution Complete: {result.dag_id}",
        f"  Duration: {result.total_duration_seconds:.1f}s",
        f"  Results: {passed} passed, {failed} failed, {total} total",
        "",
    ]

    for tr in result.results:
        status = "\u2713" if tr.success else "\u2717"
        dur = f" ({tr.duration_seconds:.1f}s)" if tr.duration_seconds else ""
        lines.append(f"  {status} {tr.task_id}{dur}")
        if tr.error:
            lines.append(f"      Error: {tr.error}")
        if tr.verify_result and not tr.success:
            for check in tr.verify_result.checks:
                if not check["passed"]:
                    lines.append(f"      Failed: {check['name']}")

    if result.integration_branch:
        lines.append("")
        lines.append(f"  Integration branch: {result.integration_branch}")
        if result.global_verify:
            gv_status = "\u2713" if result.global_verify.passed else "\u2717"
            lines.append(f"  Global verify: {gv_status}")

    lines.append("")
    if result.all_passed:
        lines.append("  Next: sextant merge --task-id <task-id>")
    else:
        lines.append(f"  Fix {failed} failed task(s) and re-run: sextant run --dag-path <path>")

    lines.append("=" * 60)
    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────

def run_run(args) -> int:
    dag_path = getattr(args, "dag_path", None)
    num_workers = getattr(args, "parallel", 1)
    worktrees_dir = Path(getattr(args, "worktrees_dir", ".sextant-worktrees")).resolve()
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces")).resolve()
    states_dir = Path(getattr(args, "states_dir", ".sextant/states")).resolve()
    base_branch = getattr(args, "base_branch", "main")
    dry_run = getattr(args, "dry_run", False)

    if dag_path is None:
        # Look for DAG in traces directory
        candidates = list(Path(".").glob(".sextant/traces/*/dag.yaml"))
        if not candidates:
            print("Usage: sextant run --dag-path <path> [--parallel N] [--dry-run]")
            print("")
            print("  Execute a task DAG, running parallelizable tasks concurrently.")
            print("  Phase 2 feature — full parallel execution engine.")
            print("")
            print("  Options:")
            print("    --dag-path <path>   Path to DAG YAML file")
            print("    --parallel N        Max parallel workers (default: 1)")
            print("    --base-branch <br>  Base branch (default: main)")
            print("    --dry-run           Show execution plan without running")
            return 1
        dag_path = str(candidates[0])

    dag = load_dag(Path(dag_path))
    if dag is None:
        print(f"  Failed to load DAG from: {dag_path}")
        return 1

    errors = dag.validate()
    if errors:
        print("  DAG validation failed:")
        for e in errors:
            print(f"    - {e}")
        return 1

    print(_format_dag_summary(dag))

    if dry_run:
        print("  (dry-run) Execution plan:")
        completed: set[str] = set()
        group_num = 0
        while True:
            groups = dag.get_parallel_groups(completed)
            if not groups:
                break
            for group in groups:
                group_num += 1
                ids = [t.task_id for t in group]
                par_note = f" [parallel:{min(len(group), num_workers)}]" if len(group) > 1 else ""
                print(f"    Group {group_num}: {', '.join(ids)}{par_note}")
                completed.update(ids)
        print("")
        print("  (dry-run) After all tasks: create integration branch")
        print("  (dry-run) Then: run global verify")
        return 0

    # Create executor and run
    executor = DAGExecutor(
        dag=dag,
        worktrees_dir=worktrees_dir,
        traces_dir=traces_dir,
        states_dir=states_dir,
        base_branch=base_branch,
        max_workers=num_workers,
        dry_run=False,
    )

    result = executor.execute()
    print(_format_results_summary(result))

    return 0 if result.all_passed else 1

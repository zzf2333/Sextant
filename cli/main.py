"""Sextant CLI — flow management tools."""
from __future__ import annotations
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sextant",
        description="Sextant flow management tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── status ────────────────────────────────────────────────────────
    sp = subparsers.add_parser(
        "status",
        help="Show a read-only snapshot of a task's trace state",
    )
    sp.add_argument(
        "task_id",
        nargs="?",
        help="Task identifier (default: most recently modified trace)",
    )
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.add_argument(
        "--traces-dir",
        default=".sextant/traces",
        metavar="DIR",
        help="Path to traces directory (default: .sextant/traces)",
    )

    # ── lint (Step 2) ─────────────────────────────────────────────────
    lp = subparsers.add_parser(
        "lint",
        help="Validate minimum-trust structure of a task's trace artifacts",
    )
    lp.add_argument("task_id", nargs="?", help="Task identifier")
    lp.add_argument(
        "--traces-dir",
        default=".sextant/traces",
        metavar="DIR",
        help="Path to traces directory (default: .sextant/traces)",
    )
    lp.add_argument("--skip-lint", action="store_true",
                    help="For Sextant developer debugging only — bypasses lint checks")

    # ── tokens ────────────────────────────────────────────────────────
    tp = subparsers.add_parser(
        "tokens",
        help="Per-stage token consumption statistics across task traces",
    )
    tp.add_argument(
        "--traces-dir",
        default=".sextant/traces",
        metavar="DIR",
        help="Path to traces directory (default: .sextant/traces)",
    )
    tp.add_argument("--since", metavar="DAYS", type=int,
                    help="Limit to tasks completed within last N days")
    tp.add_argument("--task-level", metavar="LEVELS",
                    help="Comma-separated levels to include, e.g. L1,L2")
    tp.add_argument("--detail", metavar="TASK_ID",
                    help="Show per-stage input/output breakdown for a single task")
    tp.add_argument("--json", action="store_true", help="Output as JSON")

    # ── record-usage ─────────────────────────────────────────────────
    rp = subparsers.add_parser(
        "record-usage",
        help="Record actual token and time consumption for a completed stage",
    )
    rp.add_argument(
        "--stage",
        required=True,
        choices=["spec", "review-spec", "plan", "review-plan", "build", "review-build", "record"],
        help="Stage that was completed",
    )
    rp.add_argument("--input", dest="input_tokens", required=True, type=int,
                    metavar="N", help="Input token count")
    rp.add_argument("--output", dest="output_tokens", required=True, type=int,
                    metavar="N", help="Output token count")
    rp.add_argument("--cache-read", type=int, default=0, metavar="N",
                    help="Cache read token count (prompt cache hits)")
    rp.add_argument("--cache-creation", type=int, default=0, metavar="N",
                    help="Cache creation token count")
    rp.add_argument("--started-at", metavar="ISO8601",
                    help="Stage start timestamp (e.g. 2026-04-20T10:00:00Z)")
    rp.add_argument("--completed-at", metavar="ISO8601",
                    help="Stage completion timestamp (e.g. 2026-04-20T10:08:30Z)")
    rp.add_argument("--duration", type=int, metavar="SECONDS",
                    help="Stage duration in seconds (computed from timestamps if omitted)")
    rp.add_argument("--model", metavar="MODEL",
                    help="Model used for this stage (e.g. claude-sonnet-4-6)")
    rp.add_argument("--task-id", metavar="TASK_ID",
                    help="Task identifier (default: most recently modified trace)")
    rp.add_argument(
        "--traces-dir",
        default=".sextant/traces",
        metavar="DIR",
        help="Path to traces directory (default: .sextant/traces)",
    )

    # ── metrics (Step 3) ─────────────────────────────────────────────
    mp = subparsers.add_parser(
        "metrics",
        help="Aggregate reviewer health metrics across completed tasks",
    )
    mp.add_argument(
        "--traces-dir",
        default=".sextant/traces",
        metavar="DIR",
        help="Path to traces directory (default: .sextant/traces)",
    )
    mp.add_argument("--since", metavar="DAYS", type=int,
                    help="Limit to tasks completed within last N days")
    mp.add_argument("--task-level", metavar="LEVELS",
                    help="Comma-separated levels to include, e.g. L1,L2")
    mp.add_argument("--json", action="store_true", help="Output as JSON")

    # ── v2 commands ──────────────────────────────────────────────────

    # init
    ip = subparsers.add_parser(
        "init",
        help="Initialize Sextant v2 in a project",
    )
    ip.add_argument("--project-root", default=".", metavar="DIR",
                    help="Project root directory (default: current)")
    ip.add_argument("--force", action="store_true",
                    help="Force initialization (e.g., update .gitignore)")

    # spec
    scp = subparsers.add_parser(
        "spec",
        help="Generate a task specification for the Planner",
    )
    scp.add_argument("description", nargs="?",
                     help="Task description (natural language)")
    scp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")

    # plan
    plp = subparsers.add_parser(
        "plan",
        help="Generate implementation plan and TASK_CONTRACT",
    )
    plp.add_argument("--task-id", metavar="ID", help="Task identifier")
    plp.add_argument("--task-type", default="implementation", metavar="TYPE",
                     choices=["foundation", "implementation", "integration"],
                     help="Task type (default: implementation)")
    plp.add_argument("--parallel", action="store_true",
                     help="Mark task as parallelizable")
    plp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")

    # execute
    exp = subparsers.add_parser(
        "execute",
        help="Execute a task in an isolated git worktree",
    )
    exp.add_argument("--task-id", metavar="ID", required=True, help="Task identifier")
    exp.add_argument("--contract-path", metavar="PATH",
                     help="Path to TASK_CONTRACT.md")
    exp.add_argument("--base-branch", default="main", metavar="BRANCH",
                     help="Base branch for worktree (default: main)")
    exp.add_argument("--runtime", default="reasonix", metavar="RUNTIME",
                     help="Executor runtime (default: reasonix)")
    exp.add_argument("--worktrees-dir", default=".sextant-worktrees", metavar="DIR",
                     help="Worktrees parent directory")
    exp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")
    exp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")
    exp.add_argument("--dry-run", action="store_true",
                     help="Show what would happen without executing")

    # verify
    vp = subparsers.add_parser(
        "verify",
        help="Run deterministic verification against a task",
    )
    vp.add_argument("--task-id", metavar="ID", help="Task identifier (omit for all)")
    vp.add_argument("--global", action="store_true",
                    help="Run global (integration-level) verification")
    vp.add_argument("--worktrees-dir", default=".sextant-worktrees", metavar="DIR",
                     help="Worktrees parent directory")
    vp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")

    # review
    rvp = subparsers.add_parser(
        "review",
        help="Invoke Reviewer to inspect a task's output",
    )
    rvp.add_argument("--task-id", metavar="ID", help="Task identifier")
    rvp.add_argument("--stage", default="build", metavar="STAGE",
                     choices=["spec", "plan", "build"],
                     help="Review stage (default: build)")
    rvp.add_argument("--backend", default="file", metavar="BACKEND",
                     choices=["file", "claude", "codex"],
                     help="Review backend (default: file)")
    rvp.add_argument("--model", default="claude-sonnet-4-6", metavar="MODEL",
                     help="Model to use (default: claude-sonnet-4-6)")
    rvp.add_argument("--worktrees-dir", default=".sextant-worktrees", metavar="DIR",
                     help="Worktrees parent directory")
    rvp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")
    rvp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")

    # run (parallel — Phase 2)
    rnp = subparsers.add_parser(
        "run",
        help="Execute a task DAG with parallel workers (Phase 2)",
    )
    rnp.add_argument("--dag-path", metavar="PATH",
                     help="Path to DAG YAML file")
    rnp.add_argument("--parallel", metavar="N", type=int, default=1,
                     help="Max parallel workers (default: 1)")
    rnp.add_argument("--base-branch", default="main", metavar="BRANCH",
                     help="Base branch (default: main)")
    rnp.add_argument("--worktrees-dir", default=".sextant-worktrees", metavar="DIR",
                     help="Worktrees parent directory")
    rnp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")
    rnp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")
    rnp.add_argument("--dry-run", action="store_true",
                     help="Show task grouping without executing")

    # merge
    mgp = subparsers.add_parser(
        "merge",
        help="Merge a reviewed task into the target branch",
    )
    mgp.add_argument("--task-id", metavar="ID", help="Task identifier")
    mgp.add_argument("--integration", metavar="DAG_ID",
                     help="Merge integration branch (from sextant run)")
    mgp.add_argument("--target-branch", default="main", metavar="BRANCH",
                     help="Target branch for merge (default: main)")
    mgp.add_argument("--force", action="store_true",
                     help="Force merge even if state is not APPROVED")
    mgp.add_argument("--resolve", metavar="STRATEGY",
                     choices=["ours", "theirs"],
                     help="Auto-resolve merge conflicts (ours|theirs)")
    mgp.add_argument("--dry-run", action="store_true",
                     help="Show what would happen without executing")
    mgp.add_argument("--worktrees-dir", default=".sextant-worktrees", metavar="DIR",
                     help="Worktrees parent directory")
    mgp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")

    # queue (merge queue management)
    qp = subparsers.add_parser(
        "queue",
        help="Manage the merge queue",
    )
    qp.add_argument("action", nargs="?", default="list",
                    choices=["list", "add", "remove", "process", "pause", "resume", "clear"],
                    help="Queue action (default: list)")
    qp.add_argument("--task-id", metavar="ID", help="Task identifier (for add/remove)")
    qp.add_argument("--states-dir", default=".sextant/states", metavar="DIR",
                     help="Path to state files directory")

    # compress (context compression)
    cmp = subparsers.add_parser(
        "compress",
        help="Compress old task traces to save context space",
    )
    cmp.add_argument("--since", metavar="DAYS", type=int,
                     help="Compress tasks older than N days")
    cmp.add_argument("--task-id", metavar="ID",
                     help="Compress a specific task trace")
    cmp.add_argument("--all-completed", action="store_true",
                     help="Compress all completed tasks")
    cmp.add_argument("--traces-dir", default=".sextant/traces", metavar="DIR",
                     help="Path to traces directory")
    cmp.add_argument("--dry-run", action="store_true",
                     help="Show what would be compressed without doing it")

    args = parser.parse_args()

    # ── v1 commands ──
    if args.command == "status":
        from cli.status import run_status
        sys.exit(run_status(args))

    elif args.command == "lint":
        from cli.lint import run_lint
        sys.exit(run_lint(args))

    elif args.command == "tokens":
        from cli.tokens import run_tokens
        sys.exit(run_tokens(args))

    elif args.command == "record-usage":
        from cli.tokens import run_record_usage
        sys.exit(run_record_usage(args))

    elif args.command == "metrics":
        from cli.metrics import run_metrics
        sys.exit(run_metrics(args))

    # ── v2 commands ──
    elif args.command == "init":
        from cli.init import run_init
        sys.exit(run_init(args))

    elif args.command == "spec":
        from cli.spec import run_spec
        sys.exit(run_spec(args))

    elif args.command == "plan":
        from cli.plan import run_plan
        sys.exit(run_plan(args))

    elif args.command == "execute":
        from cli.execute import run_execute
        sys.exit(run_execute(args))

    elif args.command == "verify":
        from cli.verify import run_verify
        sys.exit(run_verify(args))

    elif args.command == "review":
        from cli.review import run_review_cmd
        sys.exit(run_review_cmd(args))

    elif args.command == "run":
        from cli.run import run_run
        sys.exit(run_run(args))

    elif args.command == "merge":
        from cli.merge import run_merge
        sys.exit(run_merge(args))

    elif args.command == "queue":
        from cli.queue_cmd import run_queue
        sys.exit(run_queue(args))

    elif args.command == "compress":
        from cli.compress import run_compress
        sys.exit(run_compress(args))


if __name__ == "__main__":
    main()

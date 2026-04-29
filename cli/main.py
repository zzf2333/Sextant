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

    args = parser.parse_args()

    if args.command == "tokens":
        from cli.tokens import run_tokens
        sys.exit(run_tokens(args))

    elif args.command == "record-usage":
        from cli.tokens import run_record_usage
        sys.exit(run_record_usage(args))

    elif args.command == "status":
        from cli.status import run_status
        sys.exit(run_status(args))

    elif args.command == "lint":
        from cli.lint import run_lint
        sys.exit(run_lint(args))

    elif args.command == "metrics":
        from cli.metrics import run_metrics
        sys.exit(run_metrics(args))


if __name__ == "__main__":
    main()

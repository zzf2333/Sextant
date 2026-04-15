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

    if args.command == "status":
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

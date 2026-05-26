"""
sextant spec — generate a task specification.

In v2, this command prepares the task context for the Planner (Claude/Codex).
It reads the existing core/roles/spec.md role and produces a spec artifact
using the same template.
"""
from __future__ import annotations
import sys
from pathlib import Path

from cli.parsers import parse_frontmatter


def run_spec(args) -> int:
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces"))
    task_desc = getattr(args, "description", None)

    if not task_desc:
        print("Usage: sextant spec <task description>")
        print("")
        print("  Define a task specification for the Planner to process.")
        print("  The spec role prompt is at core/roles/spec.md")
        print("  The spec template is at core/templates/spec.md")
        print("")
        print("  Provide a task description to proceed.")
        return 1

    print(f"Task spec initiated: {task_desc[:80]}...")
    print("")
    print("  The Planner (Claude/Codex) will:")
    print("    1. Read core/roles/spec.md for the spec role contract")
    print("    2. Read .sextant/SEXTANT.md for project constraints")
    print("    3. Read modules/*/EVOLUTION.md for relevant history")
    print("    4. Fill core/templates/spec.md with:")
    print("       - scope (in/out of scope)")
    print("       - constraints")
    print("       - ambiguities")
    print("       - acceptance criteria")
    print("       - open_decisions")
    print("")
    print("  After spec is complete, run: sextant plan")
    return 0

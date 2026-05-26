"""
sextant plan — generate an implementation plan and task contract.

In v2, the plan stage produces BOTH a plan.md (similar to v1) AND a
TASK_CONTRACT.md for the Executor Worker. If the task can be decomposed
into sub-tasks, it also generates a task DAG.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

from cli.contract import TaskContract, generate_contract
from cli.parsers import parse_frontmatter, parse_section


def run_plan(args) -> int:
    traces_dir = Path(getattr(args, "traces_dir", ".sextant/traces"))
    task_id = getattr(args, "task_id", None)
    task_type = getattr(args, "task_type", "implementation")
    parallel = getattr(args, "parallel", False)

    # Try to read spec if task_id is provided
    spec_path = None
    contract: Optional[TaskContract] = None

    if task_id:
        spec_path = traces_dir / task_id / "spec.md"
        if not spec_path.exists():
            print(f"  Spec not found for task '{task_id}' at {spec_path}")
            print("  Run 'sextant spec <description>' first.")
            return 1

        # Read spec for context
        try:
            fm, text = parse_frontmatter(spec_path.read_text(encoding="utf-8")), ""
            text = spec_path.read_text(encoding="utf-8")
            fm, text = parse_frontmatter(text), text
            scope_section = parse_section(text, "scope") or ""
            constraints_section = parse_section(text, "constraints") or ""
            acceptance_section = parse_section(text, "acceptance") or ""

            # Derive objective from scope
            scope_lines = [
                l.strip("- ").strip() for l in scope_section.splitlines()
                if l.strip().startswith("-") and "<!--" not in l
            ]
            objective = scope_lines[0] if scope_lines else task_id

            # Derive acceptance from spec acceptance section
            acceptance_lines = [
                l.strip("- [ ] ").strip() for l in acceptance_section.splitlines()
                if "- [ ]" in l and "<!--" not in l
            ]

            contract = TaskContract(
                task_id=task_id,
                task_type=task_type,
                parallelizable=parallel,
                depends_on=[],
                objective=objective,
                allowed_paths=[],  # to be filled by Planner
                forbidden_paths=[],  # to be filled by Planner
                constraints=[],  # to be filled by Planner
                acceptance=acceptance_lines,
                review_focus=[],
            )
        except Exception as e:
            print(f"  Error reading spec: {e}")
            return 1

    elif task_id:
        print(f"Spec not found for task '{task_id}'")
        print("Run 'sextant spec <description>' first.")
        return 1

    else:
        print("Usage: sextant plan --task-id <id> [--task-type implementation] [--parallel]")
        print("")
        print("  Generate an implementation plan and TASK_CONTRACT.")
        print("  The Planner role prompt is at core/roles/planner.md")
        print("  The plan template is at core/templates/plan.md")
        print("  The contract template is at core/templates/task-contract.md")
        return 1

    # Output contract
    if contract:
        contract_md = contract.to_markdown()
        print(contract_md)
        print("")
        print("  Next: review the TASK_CONTRACT above, fill allowed_paths/forbidden_paths,")
        print("  then run: sextant execute --task-id", task_id)
    else:
        print("  Plan stage ready. Fill core/templates/plan.md")
        print(f"  Then generate TASK_CONTRACT.md for task '{task_id}'")
        print("  Then run: sextant execute --task-id", task_id)

    return 0

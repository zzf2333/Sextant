# /sextant-verify

> **Future CLI equivalent:** `sextant verify`

Runs the Verify stage for the current task. Verify is two layers:
1. Deterministic toolchain (tests, lint, type checks)
2. Reviewer on the build diff (stage: build)

Requires Gate 3 to have passed (build summary complete, no blocking scope_creep_flags).

## Usage

```
/sextant-verify [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 3 check**: Verify `.sextant/traces/<task_id>/build-summary.md` exists with no
   unresolved `scope_creep_flags`. If gate is not passed, print the failure reason and stop.

   **Lint pre-check**: Run `sextant lint <task_id>` before proceeding. If it exits with
   code 1 (errors found), display the lint report and stop — do not invoke the reviewer
   until lint passes. Warnings (exit 0) are displayed but do not block.

2. **Layer 1 — Deterministic toolchain**:
   - Read the `verify_commands` from `SEXTANT.md` if present (e.g. `npm test`, `npx tsc`, `npm run lint`)
   - If no `verify_commands` in `SEXTANT.md`, ask the user: "What commands should I run to
     verify this project? (tests, type check, lint)"
   - Run each command via Bash and capture output
   - If any command fails: display the failure output and stop. Do not invoke reviewer until
     all tools pass.

3. **Layer 2 — Reviewer (build stage)**:
   Once all tools pass, invoke `sextant-reviewer` subagent with:
   - `stage: build`
   - The build diff (read from git diff or recent file changes)
   - The build summary from `.sextant/traces/<task_id>/build-summary.md`
   - The approved spec and plan artifacts
   - The tool output from Layer 1

4. **Save review**: Write reviewer output to `.sextant/traces/<task_id>/review-build.md`

5. **Check `deletion_proposals`**: The field must be present and non-empty (even if `none`).
   If missing, the review artifact is malformed — request a new review from the subagent.

6. **Report verdict**: Display verdict and conditions. If `rejected`, list conditions and stop.

7. **Prompt for next step** (if approved): "Verify passed. Run `/sextant-record` to complete
   the task."

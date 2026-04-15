# /sextant-build

> **Future CLI equivalent:** `sextant build`

Starts the Build stage for the current task. Requires a reviewer-approved plan (Gate 2 passed).
Invokes the `sextant-builder` subagent to implement the recommended plan candidate.

## Usage

```
/sextant-build [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 2 check**: Verify `.sextant/traces/<task_id>/plan.md` exists and
   `.sextant/traces/<task_id>/review-plan.md` has `verdict: approved`.
   If gate is not passed, print the gate failure reason and stop.

2. **Display plan summary**: Print the recommended candidate name, rationale summary,
   and engineering footprint from the approved plan.

3. **Confirm with user**: "Proceeding with: <recommended candidate>. Continue? [y/n]"

4. **Invoke `sextant-builder` subagent** with:
   - Path to the approved spec artifact
   - Path to the approved plan artifact
   - Path to `SEXTANT.md` and `hook-registry.json` if present

5. **Builder performs implementation**: The subagent makes the actual code changes.

6. **Save build summary**: Write the subagent's build summary output to
   `.sextant/traces/<task_id>/build-summary.md`

7. **Check scope_creep_flags**: If `scope_creep_flags` is non-empty, display each flag
   and ask: "These items were added beyond plan scope. Accept (amend plan), reject, or defer?"

8. **Prompt for next step** (if no blocking flags): "Build complete. Run `/sextant-verify`
   to run the verification layer."

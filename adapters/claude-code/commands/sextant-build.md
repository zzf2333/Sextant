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

1. **Gate 2 check**: follow `core/snippets/check-upstream-gate.md` with `stage=plan`.

   On failure, print the specific reason (missing file or rejected verdict), then:
   ```
   Gate 2 failed. Run /sextant-plan (or /sextant) to produce an approved plan first.
   ```
   Stop.

2. **Display plan summary**: Print the recommended candidate name, rationale summary,
   and engineering footprint from the approved plan.

3. **Confirm with user**: "Proceeding with: <recommended candidate>. Continue? [y/n]"

4. **Invoke `sextant-builder` subagent** with:
   - Path to the approved spec artifact
   - Path to the approved plan artifact
   - Path to `.sextant/SEXTANT.md` and `.sextant/hook-registry.json` if present

5. **Builder performs implementation**: The subagent makes the actual code changes.

6. **Save build summary**: Write the subagent's build summary output to
   `.sextant/traces/<task_id>/build-summary.md`

7. **Record usage**: call `sextant record-usage` for the build stage.
   Use actual token counts from the API response if available; otherwise estimate from file sizes.

   ```bash
   sextant record-usage --stage build \
     --input <input_tokens> --output <output_tokens> \
     --cache-read <cache_read_tokens> --cache-creation <cache_creation_tokens> \
     --started-at <build_started_at> --completed-at <build_completed_at> \
     --model <model_id> --task-id <task_id>
   ```

   If the CLI is not installed, skip this step silently.

9. **Check scope_creep_flags**: if `scope_creep_flags` is non-empty, display each flag
   and ask: "These items were added beyond plan scope. Accept (amend plan), reject, or defer?"
   Do not proceed to verify until all flags are resolved.

10. **Prompt for next step** (if no blocking flags):
   ```
   Build complete.

   Run /sextant to verify and close this task.
   (Or /sextant-verify for explicit verification control.)
   ```

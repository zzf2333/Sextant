# /sextant-spec

> **Future CLI equivalent:** `sextant spec`

Starts the Spec stage for a new task or re-runs the spec subagent on an existing trace.
Classifies the task, loads project knowledge, produces a spec, and automatically runs
the reviewer — so the trace is gate-ready when this command finishes.

## Usage

```
/sextant-spec [--force-l0|--force-l1|--force-l2] [task description]
/sextant-spec <task_id>    # re-run spec subagent on existing trace
```

If no task description is provided, ask the user: "What do you want to accomplish?"

## Workflow

1. **Classify the task** using `core/rules/task-classification.md`:
   - Read the task description and check for hard keyword triggers (L2 auto-elevate)
   - Apply heuristic indicators for L0/L1/L2
   - Display classification result: `Task level: <L0|L1|L2> — Reason: <...>`
   - If `--force-*` is provided, apply override and record it with the stated reason

2. **Resolve trace directory**:
   - If `task_id` argument matches an existing `.sextant/traces/<task_id>/` directory:
     use that trace (re-run mode — skips to step 5).
   - Otherwise: create `.sextant/traces/<task_id>/` where `task_id` is a short
     date-slug (e.g. `2026-04-15-login-fix`). If that path already exists, append
     `-2`, `-3`, etc. until the path is unique.

3. **For L0 tasks**: keep the trace visible. If the user explicitly forced L0 for a
   micro-task, a minimal spec is acceptable, but it must still include
   `forced_level: true` and a non-empty `override_reason`. Do not mark the task
   complete here; even L0 work still needs Verify and Record before closure.

4. **Load knowledge context**: load all project knowledge files before invoking the spec
   subagent. This is how past tasks inform new ones. Load and pass to subagent:
   - `.sextant/SEXTANT.md` (required — if missing, note it and continue without)
   - `.sextant/PROJECT_EVOLUTION_LOG.md` if present
   - All `modules/*/EVOLUTION.md` files if present
   - `.sextant/hook-registry.json` if present

   Missing files are skipped silently — their absence means no history yet.

5. **Invoke `sextant-spec` subagent** with:
   - The task description and task_id
   - All knowledge files loaded in step 4
   - Instruction: treat the knowledge context as established constraints, not suggestions

6. **Save artifact**: write the subagent's output to `.sextant/traces/<task_id>/spec.md`

7. **Auto-review**: invoke `sextant-reviewer` subagent (spec stage) with:
   - `stage: spec`
   - The spec artifact just produced

   Save reviewer output to `.sextant/traces/<task_id>/review-spec.md`.

8. **Record usage**: call `sextant record-usage` for both stages completed in this command.
   Use actual token counts from the API response if available; otherwise estimate from file sizes.

   ```bash
   sextant record-usage --stage spec \
     --input <input_tokens> --output <output_tokens> \
     --cache-read <cache_read_tokens> --cache-creation <cache_creation_tokens> \
     --started-at <spec_started_at> --completed-at <spec_completed_at> \
     --model <model_id> --task-id <task_id>

   sextant record-usage --stage review-spec \
     --input <input_tokens> --output <output_tokens> \
     --cache-read <cache_read_tokens> --cache-creation <cache_creation_tokens> \
     --started-at <review_started_at> --completed-at <review_completed_at> \
     --model <model_id> --task-id <task_id>
   ```

   If the CLI is not installed, skip this step silently.

9. **Report verdict**:

   If `approved` or `approved-with-conditions` (all conditions resolvable):
   ```
   Spec approved. Run /sextant-plan to produce and review the implementation plan.
   (Or run /sextant — it will continue from here automatically.)
   ```

   If `rejected` or `approved-with-conditions` (with blocking unresolved conditions):
   Display the reviewer's concerns. Print:
   ```
   Spec needs revision. Address the concerns above, then:
     /sextant-spec <task_id>              re-run the spec subagent on this trace
     /sextant "<revised description>"     start fresh with a new description
   ```
   Stop.

## Notes

- Task level is set here and does not change without `--force-*`.
- Knowledge loading is unconditional — always load all available files.
- The spec reviewer runs automatically at the end of this command. Gate 1 (required
  by `/sextant-plan`) checks for the `review-spec.md` this command produces.
- Do not proceed to Plan until the spec has been reviewer-approved.
- Do not present Spec completion as task completion. A task is closed only after
  Verify and Record produce `review-build.md` and `record.md`.

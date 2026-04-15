# /sextant-spec

> **Future CLI equivalent:** `sextant spec`

Starts the Spec stage for a new task. Classifies the task level, loads all project knowledge,
then invokes the `sextant-spec` subagent to produce a structured spec artifact.

## Usage

```
/sextant-spec [--force-l0|--force-l1|--force-l2] [task description]
```

If no task description is provided, ask the user: "What do you want to accomplish?"

## Workflow

1. **Classify the task** using `core/rules/task-classification.md`:
   - Read the task description and check for hard keyword triggers (L2 auto-elevate)
   - Apply heuristic indicators for L0/L1/L2
   - Display classification result: `Task level: <L0|L1|L2> — Reason: <...>`
   - If `--force-*` is provided, apply override and record it with the stated reason

2. **Create trace directory**: `.sextant/traces/<task_id>/` where `task_id` is a short
   date-slug (e.g. `2026-04-15-login-fix`). Create `task_id` from the task description.

3. **For L0 tasks**: Ask if the user wants to proceed with full Spec stage or use `--force-l0`
   to skip Spec and Plan (going directly to Build). If skipping, create a minimal trace record.

4. **Load knowledge context**: Load all project knowledge files before invoking the spec
   subagent. This is how past tasks inform new ones — every completed task's Record stage
   writes to these files, and every new Spec reads them. Load and pass to subagent:
   - `SEXTANT.md` (required — current technical constraints, defaults, explicit no-go rules)
   - `PROJECT_EVOLUTION_LOG.md` if present (cross-module decisions and architecture history)
   - All `modules/*/EVOLUTION.md` files for any module the task touches (glob all, pass relevant ones)
   - `hook-registry.json` if present (deterministic guardrails already established)

   If a file doesn't exist yet, skip it — do not error. Missing files mean no history yet.

5. **Invoke `sextant-spec` subagent** with:
   - The task description and task_id
   - All knowledge files loaded in step 4
   - Instruction: treat the knowledge context as established constraints, not suggestions

6. **Save artifact**: Write the subagent's output to `.sextant/traces/<task_id>/spec.md`

7. **Prompt for next step**: "Spec complete. Run `/sextant-review --stage spec` to get reviewer
   feedback, or `/sextant-plan` if you want to skip spec review (L0 only)."

## Notes

- Do not proceed to Plan until the spec has been reviewer-approved (Gate 1).
- Task level is set here and does not change without `--force-*`.
- Knowledge loading is unconditional — always load all available files, not just when the
  task description mentions a specific module. Past decisions apply across the board.

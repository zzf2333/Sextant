# /sextant-spec

> **Future CLI equivalent:** `sextant spec`

Starts the Spec stage for a new task. Classifies the task level, then invokes the
`sextant-spec` subagent to produce a structured spec artifact.

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

4. **Invoke `sextant-spec` subagent** with:
   - The task description and task_id
   - The path to `SEXTANT.md` (look in the project root)
   - Paths to relevant `modules/*/EVOLUTION.md` if the task mentions a specific module

5. **Save artifact**: Write the subagent's output to `.sextant/traces/<task_id>/spec.md`

6. **Prompt for next step**: "Spec complete. Run `/sextant-review --stage spec` to get reviewer
   feedback, or `/sextant-plan` if you want to skip spec review (L0 only)."

## Notes

- Do not proceed to Plan until the spec has been reviewer-approved (Gate 1).
- Task level is set here and does not change without `--force-*`.

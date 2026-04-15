# /sextant-plan

> **Future CLI equivalent:** `sextant plan`

Starts the Plan stage for the current task. Requires a reviewer-approved spec (Gate 1 passed).
Invokes the `sextant-planner` subagent, then invokes the reviewer on the resulting plan.

## Usage

```
/sextant-plan [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 1 check**: Verify `.sextant/traces/<task_id>/spec.md` exists and contains a
   reviewer-approved review artifact at `.sextant/traces/<task_id>/review-spec.md` with
   `verdict: approved` or `verdict: approved-with-conditions` (all conditions resolved).
   If gate is not passed, print the gate failure reason and stop.

2. **Invoke `sextant-planner` subagent** with:
   - Path to the approved spec artifact
   - Path to `SEXTANT.md`
   - Paths to relevant `modules/*/EVOLUTION.md` and `hook-registry.json` if present

3. **Save artifact**: Write the subagent's output to `.sextant/traces/<task_id>/plan.md`

4. **Invoke reviewer (plan stage)**: Automatically invoke `sextant-reviewer` subagent with:
   - `stage: plan`
   - The plan artifact just produced

5. **Save review**: Write reviewer output to `.sextant/traces/<task_id>/review-plan.md`

6. **Report verdict**: Display the reviewer's verdict and any conditions.
   If `rejected` or `approved-with-conditions`, list the conditions clearly.

7. **Prompt for next step** (if approved): "Plan approved. Run `/sextant-build` to begin
   implementation."

# /sextant-plan

> **Future CLI equivalent:** `sextant plan`

Starts the Plan stage for the current task. Requires a reviewer-approved spec (Gate 1 passed).
Invokes the `sextant-planner` subagent, then automatically invokes the reviewer on the
resulting plan.

## Usage

```
/sextant-plan [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 1 check**: follow `core/snippets/check-upstream-gate.md` with `stage=spec`.

   On failure, print the specific reason (missing file or rejected verdict), then:
   ```
   Gate 1 failed. Run /sextant-spec (or /sextant) to produce an approved spec first.
   ```
   Stop.

2. **Invoke `sextant-planner` subagent** with:
   - Path to the approved spec artifact
   - Path to `.sextant/SEXTANT.md`
   - Paths to relevant `modules/*/EVOLUTION.md` and `.sextant/hook-registry.json` if present

3. **Save artifact**: write the subagent's output to `.sextant/traces/<task_id>/plan.md`

4. **Auto-review**: invoke `sextant-reviewer` subagent (plan stage) with:
   - `stage: plan`
   - The plan artifact just produced

5. **Save review**: write reviewer output to `.sextant/traces/<task_id>/review-plan.md`

6. **Report verdict**: display the reviewer's verdict and any conditions.

   If `approved` or `approved-with-conditions`:
   Display plan summary (recommended candidate, rationale, engineering footprint). Print:
   ```
   Plan approved. Review the plan above, then:
     /sextant         proceed to Build automatically
     /sextant-build   explicit build stage control
   ```

   If `rejected` or `changes-requested`:
   Display each condition clearly. Print:
   ```
   Plan needs revision. Address the concerns above, then run /sextant-plan again.
   ```
   Stop.

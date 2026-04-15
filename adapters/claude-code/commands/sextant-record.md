# /sextant-record

> **Future CLI equivalent:** `sextant record`

Runs the Record stage for the current task. Completes the P5 writebacks checklist and
updates knowledge files. Closes the task trace.

## Usage

```
/sextant-record [task_id]
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 4 check**: Verify `.sextant/traces/<task_id>/review-build.md` exists with
   `verdict: approved`. If gate is not passed, print the failure reason and stop.

2. **Present P5 checklist** and ask the user to answer each question:

   ```
   P5 Writebacks Checklist for task: <task_id>

   1. Did this task change global technical constraints or defaults? (SEXTANT.md)
   2. Did this task produce a design/spec/plan lesson for a specific module? (modules/*/EVOLUTION.md)
   3. Did this task produce a cross-module or project-level decision? (PROJECT_EVOLUTION_LOG.md)
   4. Did this task reveal an execution failure preventable by a deterministic check? (hook-registry.json)

   Answer each: yes / no
   ```

3. **For each "yes" answer**: Guide the user to compose the knowledge writeback entry and
   apply it to the appropriate file. Use `Read` to load the current file content, then `Edit`
   to apply the update.

4. **Build record artifact**: Create a filled `record` following `core/templates/record.md`
   with the checklist answers and writeback entries (or `skip_reason` if all "no").
   Write to `.sextant/traces/<task_id>/record.md`

5. **Close the trace**: Append to `.sextant/traces/index.md` (create if absent):
   ```
   | <task_id> | <task_level> | <completed_at> | <one-line summary> |
   ```

6. **Final summary**: Print:
   ```
   Task <task_id> complete.
   Level: L1 | Writebacks: 2 | Trace: .sextant/traces/<task_id>/
   ```

# /sextant-record

> **Future CLI equivalent:** `sextant record`

Runs the Record stage for the current task. Closes the knowledge loop: what gets written
here is what the next task's Spec stage will load as context.

Supports a **fast-close path** for tasks with no durable knowledge delta, and a full
P5 writeback flow for tasks that produced meaningful changes.

## Usage

```
/sextant-record [task_id]
/sextant-record [task_id] --full   # force full P5 flow even if fast-close eligible
```

If `task_id` is not provided, look for the most recent task directory in `.sextant/traces/`.

## Workflow

1. **Gate 4 check**: follow `core/snippets/check-upstream-gate.md` with `stage=build`.

   On failure: print the specific reason, then:
   ```
   Gate 4 failed. Run /sextant-verify (or /sextant) to pass verification first.
   ```
   Stop.

2. **Analyze for durable knowledge signals** (unless `--full` flag provided):

   Scan `build-summary.md` and the recent diff for indicators:
   - New directories under `modules/` → signals EVOLUTION.md entry needed
   - New dependencies in `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml` → signals `.sextant/SEXTANT.md` update
   - Cross-module changes (more than 2 modules touched) → signals `.sextant/PROJECT_EVOLUTION_LOG.md` entry
   - Keywords in build-summary: "redesign", "migrate", "replace", "deprecate", "new pattern",
     "new constraint", "removed", "breaking" → signals likely architectural record
   - Unresolved scope_creep_flags that were deferred → signals follow-up tracking

   Assign each signal a target file (`.sextant/SEXTANT.md` / EVOLUTION.md / `.sextant/PROJECT_EVOLUTION_LOG.md` /
   `.sextant/hook-registry.json`).

3. **Fast-close path** (if no signals AND `--full` not set):

   Print:
   ```
   ── Record: fast close ───────────────────────────────
   No durable knowledge delta detected in this task.

   Close without knowledge writebacks? [y/n]
   (Use /sextant-record --full to run the complete P5 flow.)
   ─────────────────────────────────────────────────────
   ```

   If "y": create `record.md` with all P5 answers set to "no" and
   `skip_reason: "No durable changes detected by signal analysis."` then go to Step 6.

   If "n": continue with full P5 flow (Step 4).

4. **Full P5 checklist** (if signals found, `--full` set, or user declined fast-close):

   Present each question with a pre-analyzed recommendation where available:

   ```
   P5 Writebacks for task: <task_id>

   1. Did this task change global technical constraints or defaults?
      → `.sextant/SEXTANT.md`
      [Detected: new dependency X added]  Recommended: yes

   2. Did this task produce a design/spec/plan lesson for a specific module?
      → modules/*/EVOLUTION.md
      [Detected: new module auth/ created]  Recommended: yes

   3. Did this task produce a cross-module or project-level decision?
      → `.sextant/PROJECT_EVOLUTION_LOG.md`
      [No signal detected]  Recommended: no

   4. Did this task reveal an execution failure preventable by a deterministic check?
      → `.sextant/hook-registry.json`
      [No signal detected]  Recommended: no

   Answer each: yes / no (press Enter to accept recommendation)
   ```

5. **For each "yes" answer**: draft a specific writeback entry and present it for
   confirmation before applying.

   Write entries that would change a future task's judgment — be specific about what
   changed and why, not just what was done. Vague summaries are useless to future Spec.
   Useful entries state the constraint, the trade-off accepted, or the path rejected and why.

   Use `Read` to load the current file, `Edit` to apply the update.

6. **Create record artifact**: write filled `record.md` following `core/templates/record.md`
   to `.sextant/traces/<task_id>/record.md`.

7. **Close the trace**: append to `.sextant/traces/index.md` (create if absent):
   ```
   | <task_id> | <task_level> | <completed_at> | <one-line summary> |
   ```

8. **Print final summary**:
   ```
   ── Task complete ─────────────────────────────────────
   Task:  <task_id>
   Level: <L0|L1|L2>  |  Writebacks: <n>
   Trace: .sextant/traces/<task_id>/

   Knowledge updated. The next /sextant will load these changes as context.
   ──────────────────────────────────────────────────────
   ```

## Notes

- The fast-close path does not weaken the protocol. It skips the ceremony when the
  analysis confirms there is nothing to record — not by default, but by detection.
- Use `--full` for L2 tasks or whenever you want explicit control over what gets recorded.
- These entries are exactly what the next `/sextant` or `/sextant-spec` will load as context.
  Write what will change a future engineer's judgment, not what happened.

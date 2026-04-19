# /sextant-status

> Shows where you are and what to do next.

Inspects the current task trace (or the most recent active one) and reports the
current stage, pending gate, blockers, and recommended next action.

## Usage

```
/sextant-status              # most recent active task
/sextant-status <task_id>    # specific task by ID
/sextant-status --all        # list all traces (active and complete)
```

## Workflow

### If `task_id` is provided

1. Verify `.sextant/traces/<task_id>/` exists. If not: print "Task `<task_id>` not found."

2. Inspect the trace directory to determine current stage:

   | Artifact state | Stage |
   |---|---|
   | No artifacts | Pre-spec |
   | `spec.md` only | Spec (review pending) |
   | `review-spec.md` exists, verdict approved | Ready for Plan |
   | `review-spec.md` exists, verdict rejected | Spec blocked |
   | `plan.md` only | Plan (review pending) |
   | `review-plan.md` exists, verdict approved | Ready for Build |
   | `review-plan.md` exists, verdict rejected | Plan blocked |
   | `build-summary.md` exists, scope_creep_flags unresolved | Build blocked |
   | `build-summary.md` exists, no blocking flags | Ready for Verify |
   | `review-build.md` exists, verdict approved | Ready for Record |
   | `review-build.md` exists, verdict rejected | Verify blocked |
   | `record.md` exists | Complete |

3. Read frontmatter fields from available artifacts:
   - `task_level` from `spec.md`
   - `spec_version`, `plan_version`, `review_version`, `record_version` if applicable
   - Reviewer verdict and any unresolved conditions

4. Print a status block:

   ```
   ── Task: <task_id> ──────────────────────────────────
   Level:   L1
   Stage:   Build (complete, verify pending)
   Gate:    Gate 3 — build-summary.md ✓, scope_creep_flags: none

   Next action:
     /sextant          run verify + close automatically
     /sextant-verify   explicit verify control
   ─────────────────────────────────────────────────────
   ```

   If blocked:
   ```
   ── Task: <task_id> ──────────────────────────────────
   Level:   L2
   Stage:   Plan (blocked)
   Blocker: review-plan.md verdict: rejected
             - "Engineering footprint underestimates migration risk"
             - "No rollback_path specified (required for L2)"

   Next action:
     /sextant-plan <task_id>   re-run planner with revised spec
   ─────────────────────────────────────────────────────
   ```

   If complete:
   ```
   ── Task: <task_id> ──────────────────────────────────
   Level:   L1
   Stage:   Complete ✓
   Closed:  <completed_at from record.md>
   ─────────────────────────────────────────────────────
   ```

### If no argument provided (most recent active task)

1. Scan `.sextant/traces/` for all directories.
2. Separate into active (no `record.md`) and complete (has `record.md`).
3. Sort active by modification time, newest first.
4. If one active task: show the full single-task view above.
5. If multiple active tasks: list all active tasks with a one-line summary each,
   then show the full view for the most recent one.

   ```
   Active tasks (3):
     2026-04-19-auth-rewrite      L2  Plan blocked (reviewer rejected)
     2026-04-18-fix-login-bug  →  L1  Build complete, verify pending
     2026-04-17-docs-update       L0  Complete ✓

   Showing most recent active task:
   ── Task: 2026-04-18-fix-login-bug ...
   ```

6. If no active tasks: print "No active tasks. Run `/sextant <description>` to start."

### If `--all` flag provided

List all traces (active + complete), sorted by modification time:

```
TASK                          LEVEL  STAGE    STATUS
2026-04-19-auth-rewrite       L2     Plan     blocked (reviewer rejected)
2026-04-18-fix-login-bug      L1     Build    verify pending
2026-04-17-docs-update        L0     Done     ✓ 2026-04-17
2026-04-15-schema-migration   L2     Done     ✓ 2026-04-15
```

## Notes

- This command is read-only. It does not modify any artifacts or traces.
- If the CLI tool (`sextant status`) is installed, prefer using it for machine-readable
  output: `sextant status <task_id> --json`
- Use this command to recover orientation after a context switch or session gap.

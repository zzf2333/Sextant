# /sextant

> The primary Sextant entry command. Start here for new tasks, or resume an active one.

Intelligently advances the current task to the next meaningful decision point.
Runs spec, review, and plan automatically on first invocation; then build, verify, and
record on subsequent ones. Pauses only where human judgment is actually needed.

## Usage

```
/sextant [task description]   # start a new task
/sextant                      # resume most recent active task
/sextant <task_id>            # resume a specific task by ID
```

## Design

Protocol remains intact. UX becomes simpler.

Every gate, reviewer session, and verification step still runs. This command
orchestrates them so you don't have to do it manually step by step.

**Meaningful pause points** (where the command stops and waits):

1. After plan review — you must decide whether this is the right implementation plan
2. After build — you must review scope before verification begins
3. After verify failure — reviewer or tool failures require your resolution

On a happy-path L1 task the expected sequence is:

```
/sextant "task description"   → Spec + Spec Review + Plan + Plan Review  → PAUSE
/sextant                      → Build                                     → PAUSE
/sextant                      → Verify + Record fast-close                → DONE
```

---

## Workflow

### Step 1: Resolve task context

**If a task description is provided:**

a. Generate a slug from the description (lowercase, hyphens, max 40 chars).
   Check if `.sextant/traces/<date>-<slug>/` already exists.
   If it exists: ask — "Found active task `<task_id>`. Resume it, or start a new task? [resume / new]"
   If new: proceed to Step 2 (start new task).
   If resume: proceed to Step 3 (continue from current stage).

b. If the argument looks like an existing `task_id` (matches a directory name in
   `.sextant/traces/`): treat as resume, go to Step 3.

**If no argument is provided:**

c. Find all trace directories in `.sextant/traces/` that do NOT have `record.md`.
   Sort by modification time (newest first).
   If one found: print brief status (task_id, current stage, recommended next action)
   and proceed to Step 3.
   If multiple found: list the top 3 with stages and ask which to resume.
   If none found: print "No active task. Run `/sextant <task description>` to start."

---

### Step 2: Start new task (Spec → Plan, then pause)

2a. **Classify task level** using `core/rules/task-classification.md`.
    Display: `Task level: <L0|L1|L2> — <reason>`

    For L0 tasks: ask —
    "This looks like a small task. Run the full Spec→Plan→Build→Verify→Record flow, or
    use `--force-l0` to go straight to Build? [full / build]"
    - If "build": skip to Step 3b (build stage).
    - If "full": continue with spec below.

2b. **Create trace directory**: `.sextant/traces/<task_id>/` where `task_id` is
    `<YYYY-MM-DD>-<slug>`. If the directory already exists, append `-2`, `-3`, etc.
    until the path is unique.

2c. **Load knowledge context**: read the following files if present. Skip missing files
    silently — their absence means no history yet.
    - `SEXTANT.md`
    - `PROJECT_EVOLUTION_LOG.md`
    - All `modules/*/EVOLUTION.md` files
    - `hook-registry.json`

2d. **Invoke `sextant-spec` subagent** with:
    - The task description
    - The task_id and classification level
    - All knowledge files loaded in 2c

    Save output to `.sextant/traces/<task_id>/spec.md`.

2e. **Invoke `sextant-reviewer` subagent** (spec stage) with:
    - `stage: spec`
    - The spec artifact just produced

    Save output to `.sextant/traces/<task_id>/review-spec.md`.

2f. **Check spec verdict.**
    If verdict is `rejected` or `approved-with-conditions` (with unresolved conditions):
      Display the reviewer's concerns clearly.
      Print:
      ```
      ── Spec review: needs revision ──────────────────────
      Address the concerns above, then either:
        /sextant "<revised description>"   start over with revised description
        /sextant-spec <task_id>            re-run spec subagent on this trace
      ─────────────────────────────────────────────────────
      ```
      Stop.

    If approved: continue.

2g. **Invoke `sextant-planner` subagent** with:
    - The approved spec artifact
    - `SEXTANT.md`, relevant `modules/*/EVOLUTION.md`, `hook-registry.json`

    Save output to `.sextant/traces/<task_id>/plan.md`.

2h. **Invoke `sextant-reviewer` subagent** (plan stage) with:
    - `stage: plan`
    - The plan artifact just produced

    Save output to `.sextant/traces/<task_id>/review-plan.md`.

2i. **Check plan verdict.**
    If rejected: display conditions. Print:
    ```
    ── Plan review: rejected ────────────────────────────
    Address the plan concerns above, then run:
      /sextant-plan <task_id>   re-run the planner with revised spec
    ─────────────────────────────────────────────────────
    ```
    Stop.

    If approved or approved-with-conditions: display the plan summary (candidate
    name, rationale in 2–3 lines, engineering footprint, reviewer verdict).

2j. **Pause — implementation decision point.**
    Print:
    ```
    ── Plan approved ────────────────────────────────────
    Review the plan above. When ready to implement:

      /sextant           proceed to Build
      /sextant-build     same, with explicit stage control
      /sextant-status    review full task state before deciding
    ─────────────────────────────────────────────────────
    ```
    Stop.

---

### Step 3: Continue from current stage

Called when resuming an active task (Step 1b or 1c).

Detect current stage by inspecting which artifacts exist in the trace directory:

**3a. Has `review-spec.md` (approved) but no `plan.md`:**
    → Run Plan + Plan Review. Go to Steps 2g–2j.

**3b. Has `review-plan.md` (approved) but no `build-summary.md`:**
    → Ready to build. Show plan summary (candidate name, footprint, 2-line rationale).

    Print: "Proceeding with: `<candidate>`. Starting build..."

    Invoke `sextant-builder` subagent with:
    - Approved spec artifact
    - Approved plan artifact
    - `SEXTANT.md` and `hook-registry.json` if present

    Save output to `.sextant/traces/<task_id>/build-summary.md`.

    Check `scope_creep_flags`. If non-empty:
      Display each flag.
      Print:
      ```
      ── Scope creep detected ─────────────────────────────
      These items exceeded plan scope. Resolve each before verifying:
        accept   → edit plan.md to include this item, then re-run build
        reject   → mark as out-of-scope in build-summary.md
        defer    → note as future work, exclude from this build
      
      Run /sextant-build <task_id> for explicit build stage control.
      ─────────────────────────────────────────────────────
      ```
      Stop.

    If no blocking flags: pause. Print:
    ```
    ── Build complete ───────────────────────────────────
    Run /sextant to verify and close this task.
    ─────────────────────────────────────────────────────
    ```
    Stop.

**3c. Has `build-summary.md` (no unresolved scope_creep_flags) but no `review-build.md`:**
    → Run Verify + Record. Go to Step 4.

**3d. Has `review-build.md` (approved) but no `record.md`:**
    → Run fast-close Record analysis. Go to Step 5.

**3e. Has `record.md`:**
    Print: "Task `<task_id>` is already complete. Run `/sextant-status` to view trace."

**3f. Has `spec.md` but no `review-spec.md`:**
    → Spec written but not reviewed yet. Run reviewer (Steps 2e–2f).

**3g. Has `review-plan.md` with unresolved conditions or verdict `rejected`:**
    → Gate blocked. Show the rejection reason. Print:
    "Plan review failed. Run `/sextant-plan <task_id>` to re-run the planner."
    Stop.

---

### Step 4: Verify (runs from Step 3c)

4a. **Gate 3 check**: confirm `build-summary.md` has no unresolved `scope_creep_flags`.
    If blocked: print the flags and stop.

4b. **Lint pre-check**: run `sextant lint <task_id>` (if the CLI is available).
    If errors (exit code 1): display the report. Stop.
    If unavailable (CLI not installed): skip and note it.

4c. **Auto-detect verify commands** if `verify_commands` is not set in `SEXTANT.md`:

    Check project root for the following signals (in order):
    - `package.json` exists → read its `scripts` field:
      - Has `test` → add `npm test`
      - Has `typecheck` or `type-check` → add `npm run typecheck` (or the exact key)
      - Has `lint` → add `npm run lint`
    - `pyproject.toml`, `pytest.ini`, `setup.cfg`, or `conftest.py` exists → add `python -m pytest`
    - `pyproject.toml` or `setup.cfg` with `[tool.ruff]` or `[tool.flake8]` → add ruff/flake8 check
    - `go.mod` exists → add `go test ./...`
    - `Cargo.toml` exists → add `cargo test`

    Print detected commands:
    "No `verify_commands` found in SEXTANT.md. Detected: [list]"
    "Proceeding. Add `verify_commands:` to SEXTANT.md to pin these permanently."

    If no commands detected: ask the user to provide them. Do not proceed until confirmed.

4d. **Run each verify command** via Bash. Capture output. If any command fails:
    Display the failure output clearly. Stop. Print:
    "Verification failed. Fix the above and run `/sextant` to retry."

4e. **Invoke `sextant-reviewer` subagent** with:
    - `stage: build`
    - The build diff (from `git diff HEAD` or recent file changes)
    - `build-summary.md`
    - Approved spec and plan artifacts
    - Tool output from Step 4d

    Save to `.sextant/traces/<task_id>/review-build.md`.

4f. **Verify `deletion_proposals` present**. If field is missing, the review is malformed —
    re-invoke the reviewer subagent (once). If still missing, stop and report the issue.

4g. **Check verdict**.
    If `rejected`: display conditions clearly. Stop. Print:
    "Build review failed. Resolve the above and run `/sextant` to re-verify."

    If approved or approved-with-conditions: continue to Step 5.

---

### Step 5: Record fast-close (runs from Step 3d or after Step 4g)

5a. **Analyze for durable knowledge signals** by reading `build-summary.md` and
    scanning recent file changes:

    Signal indicators:
    - New directories created under `modules/` → likely EVOLUTION.md entry
    - Changes to `package.json`, `pyproject.toml`, `go.mod` (new dependencies) → likely SEXTANT.md update
    - New entries in `hook-registry.json` → already recorded
    - More than 2 modules touched → likely PROJECT_EVOLUTION_LOG.md entry
    - Architecture-level keywords in build-summary ("redesign", "migrate", "replace",
      "new pattern", "deprecate") → likely EVOLUTION.md or PROJECT_EVOLUTION_LOG.md entry

5b. **If no signals found**: print:
    ```
    ── Record: fast close ───────────────────────────────
    No durable knowledge delta detected.

    Closing task without knowledge writebacks.
    Confirm? [y/n]
    ─────────────────────────────────────────────────────
    ```
    On "y": create a minimal `record.md` (all P5 answers: no, skip_reason: "No durable
    changes detected by signal analysis.") and go to Step 5d.
    On "n": run the full P5 checklist (Step 5c).

5c. **If signals found** (or user declined fast close):

    Print a pre-analyzed recommendation for each signal:
    ```
    ── Record: knowledge writebacks ─────────────────────
    Detected signals:
      [signal]: <description> → <target file>

    For each: accept and I'll draft the entry, or skip.
    ─────────────────────────────────────────────────────
    ```

    For each accepted writeback: read the target file, draft a specific entry,
    present it for confirmation, then apply it with `Edit`.

    Fill in the `record.md` artifact with the P5 checklist and writeback entries.
    Write to `.sextant/traces/<task_id>/record.md`.

5d. **Close the trace**: append to `.sextant/traces/index.md` (create if absent):
    ```
    | <task_id> | <task_level> | <completed_at> | <one-line summary> |
    ```

5e. **Print final summary**:
    ```
    ── Task complete ─────────────────────────────────────
    Task:  <task_id>
    Level: <L0|L1|L2>  |  Writebacks: <n>
    Trace: .sextant/traces/<task_id>/

    Knowledge updated. The next /sextant will load these changes as context.
    ──────────────────────────────────────────────────────
    ```

---

## Notes

- Individual stage commands (`/sextant-spec`, `/sextant-plan`, etc.) remain available for
  explicit phase control, debugging, or L2 tasks requiring step-by-step supervision.
- `/sextant-status` gives a full state dump if you need to understand where a task is.
- For L2 tasks (data model, auth, payment, sync), consider using individual stage commands
  so each gate is explicitly reviewed before proceeding.
- This command does not skip gates. Reviews still run. Knowledge writeback logic still
  applies. The difference is automation of the non-decision steps.
